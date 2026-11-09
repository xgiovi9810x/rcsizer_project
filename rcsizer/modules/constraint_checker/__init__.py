from rcsizer.core.state import DesignState, Warning

name = "constraint_checker"
version = "2.0.0"
requires = ["input", "geometry", "aero", "stability", "weights", "structure", "performance"]
provides = ["constraints"]

def run(state: DesignState) -> DesignState:
    geo = state.derived["geometry"]
    stab = state.derived["stability"]
    struct = state.derived.get("structure", {})
    w = state.derived.get("weights", {})
    perf = state.derived.get("performance", {})
    
    violated = []
    advices = []
    
    # --- C1: MARGINE STATICO ---
    SM = stab.get("SM", stab.get("SM_target", 0.0))
    if SM < 0.05:
        violated.append("C1 - Margine Statico BLOCCANTE")
        advices.append("SM troppo basso (< 5%): Sposta la batteria in avanti o aumenta l'area della coda.")
    elif SM > 0.20:
        violated.append("C1 - Margine Statico AVVISO")
        advices.append("SM troppo alto (> 20%): L'aereo sarà troppo stabile e poco manovrabile. Sposta la batteria indietro.")

    # --- C2: POSIZIONE CG (FIX N4: Aggiunto limite anteriore) ---
    h_cg = w.get("h_cg", 0.0)
    h_n = stab.get("h_n", 0.0)
    cg_fwd = stab.get("CG_fwd_limit", 0.0)
    
    if h_cg > h_n:
        violated.append("C2 - CG dietro il Neutral Point BLOCCANTE")
        advices.append("CG troppo arretrato: L'aereo è instabile. Sposta i componenti pesanti in avanti.")
    elif h_cg < cg_fwd:
        violated.append("C2 - CG troppo avanti BLOCCANTE")
        advices.append(f"CG troppo avanti ({h_cg*100:.1f}% < {cg_fwd*100:.1f}%): L'aereo non sarà in grado di alzare il muso per atterrare.")
    
    # --- C3: PROPULSIONE E AUTONOMIA (FIX N5) ---
    P_req = perf.get("P_req", 0.0)
    P_max = state.input.propulsion.motor.P_max
    endurance_h = perf.get("endurance_h", 0.0)
    
    if P_req > P_max:
        violated.append("C3 - Potenza Motore BLOCCANTE")
        advices.append(f"Il motore è troppo debole ({P_max} W < {P_req:.1f} W richiesti).")
    elif endurance_h < 0.1: # Meno di 6 minuti
        violated.append("C3 - Autonomia AVVISO")
        advices.append(f"Autonomia molto bassa ({endurance_h*60:.0f} minuti). Usa una batteria più grande.")

    # --- C5: MARGINE STRUTTURALE ---
    MS_strength = struct.get("MS_strength", 999.0)
    MS_buckling = struct.get("MS_buckling", 999.0)
    if MS_strength < 0:
        violated.append("C5 - Resistenza Strutturale BLOCCANTE")
        advices.append(f"L'ala si spezza (MS={MS_strength:.2f}). Aumenta lo spessore delle pareti.")
    if MS_buckling < 0:
        violated.append("C5 - Buckling BLOCCANTE")
        # Usa il consiglio specifico generato dal modulo struttura se disponibile
        buck_advice = struct.get("buckling_advice", "Avvicina le centine o aumenta lo spessore.")
        advices.append(f"L'ala si schiaccia (MS={MS_buckling:.2f}). {buck_advice}")

    new_state = state.with_derived(
        "constraints",
        is_valid=bool(len([v for v in violated if "BLOCCANTE" in v]) == 0),
        violations=violated,
        advices=advices
    )
    
    for v in violated:
        new_state = new_state.with_warning(Warning(
            code=v.split(" ")[0],
            severity="error" if "BLOCCANTE" in v else "warning",
            message=v
        ))
        
    return new_state
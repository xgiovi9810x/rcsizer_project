from rcsizer.core.state import DesignState, Warning

name = "constraint_checker"
version = "1.2.0"
requires = ["input", "geometry", "aero", "stability", "weights", "structure", "performance"]
provides = ["constraints"]

def run(state: DesignState) -> DesignState:
    geo = state.derived["geometry"]
    stab = state.derived["stability"]
    struct = state.derived.get("structure", {})
    w = state.derived.get("weights", {})
    
    violated = []
    advices = []
    
    SM = stab.get("SM", stab.get("SM_target", 0.0))
    if SM < 0.05:
        violated.append("C1 - Margine Statico BLOCCANTE")
        advices.append("SM troppo basso (< 5%): Sposta la batteria in avanti o aumenta l'area della coda.")
    elif SM > 0.20:
        violated.append("C1 - Margine Statico AVVISO")
        advices.append("SM troppo alto (> 20%): L'aereo sarà troppo stabile e poco manovrabile. Sposta la batteria indietro.")

    h_cg = w.get("h_cg", 0.0)
    h_n = stab.get("h_n", 0.0)
    if h_cg > h_n:
        violated.append("C2 - CG dietro il Neutral Point BLOCCANTE")
        advices.append("CG troppo arretrato: L'aereo è instabile. Sposta i componenti pesanti in avanti.")
    
    MS_strength = struct.get("MS_strength", 999.0)
    MS_buckling = struct.get("MS_buckling", 999.0)
    if MS_strength < 0:
        violated.append("C5 - Resistenza Strutturale BLOCCANTE")
        advices.append(f"L'ala si spezza (MS={MS_strength:.2f}). Aumenta lo spessore delle pareti o usa un materiale più resistente.")
    if MS_buckling < 0:
        violated.append("C5 - Buckling BLOCCANTE")
        advices.append(f"L'ala si schiaccia (MS={MS_buckling:.2f}). Avvicina le centine o aumenta lo spessore.")

    W_S = w.get("W", 0.0) / geo["S"] if geo["S"] > 0 else 0
    if W_S > 100: 
        violated.append("C4 - Carico Alare AVVISO")
        advices.append(f"Carico alare elevato ({W_S:.1f} N/m2). L'aereo atterrerà veloce. Aumenta l'area alare.")

    new_state = state.with_derived(
        "constraints",
        is_valid=bool(len([v for v in violated if "BLOCCANTE" in v]) == 0), # <-- FIX
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
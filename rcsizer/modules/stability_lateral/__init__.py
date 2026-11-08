import math
from rcsizer.core.state import DesignState, Provenance, ProvenanceKind

name = "stability_lateral"
version = "1.0.0"
requires = ["input", "geometry", "aero", "stability"]
provides = ["lateral"]

def run(state: DesignState) -> DesignState:
    geo = state.derived["geometry"]
    aero = state.derived["aero"]
    inp = state.input
    
    S = geo["S"]
    b = geo["b"]
    AR = geo["AR"]
    CL_alpha = aero["CL_alpha"]
    
    # 1. Dihedral Effect (Cl_beta) - Sez. 4.6
    # Prendiamo il diedro medio dall'input (in radianti)
    # Assumiamo che il pannello 0 sia rappresentativo o facciamo una media
    dihedral_deg = inp.wing.panels[0].dihedral * (180 / math.pi)
    dihedral_rad = inp.wing.panels[0].dihedral
    
    # Rapporto di rastremazione (Taper ratio)
    taper = inp.wing.panels[0].chord_tip / inp.wing.panels[0].chord_root
    
    # Formula Cl_beta (effetto diedro sul rollio)
    # Cl_beta = - CL_alpha * Gamma / 4 * (1+2*lambda)/(3*(1+lambda))
    # Un valore più NEGATIVO significa più stabilità laterale (rolla via dal vento)
    Cl_beta = - (CL_alpha * dihedral_rad / 4.0) * ((1 + 2*taper) / (3 * (1 + taper)))
    
    # 2. Weathercock Effect (Cn_beta) - Sez. 4.6
    # Volume di coda verticale (V_V) e pendenza di portanza della pinna
    tail = inp.tail
    S_v = tail.S_v if tail.S_v else 0.02 # Valore di default se manca
    l_v = tail.l_v if tail.l_v else 0.6
    AR_v = tail.AR_v if tail.AR_v else 2.0
    
    V_V = (S_v * l_v) / (S * b) if (S * b) > 0 else 0
    
    # Pendenza di portanza della pinna (approssimata)
    CL_alpha_v = (2 * math.pi * AR_v) / (2 + math.sqrt(4 + AR_v**2))
    eta_v = 0.9 # Efficienza pinna
    
    # Cn_beta (effetto banderuola)
    Cn_beta = V_V * CL_alpha_v * eta_v
    
    # 3. Recommended Twist (Svergolamento) - Da Lennon / Excel
    # Più l'ala è rastremata o frecciata, più c'è rischio di stallo in punta.
    # Si consiglia washout (twist negativo) da -2° a -3° per ali con taper < 0.6
    sweep_deg = inp.wing.panels[0].sweep_LE * (180 / math.pi)
    
    twist_recommended_deg = 0.0
    if taper < 0.7 or sweep_deg > 2.0:
        twist_recommended_deg = -2.0 # Svergolamento base
        if taper < 0.5 or sweep_deg > 5.0:
            twist_recommended_deg = -3.0 # Svergolamento più aggressivo
            
    # Raccomandazione Diedro (se l'utente ha messo 0, suggeriamo il minimo)
    dihedral_recommended_deg = 0.0
    if inp.wing.wing_position_z.value == "high":
        dihedral_recommended_deg = 2.0
    elif inp.wing.wing_position_z.value == "mid":
        dihedral_recommended_deg = 3.0
    else:
        dihedral_recommended_deg = 4.0
        
    # Aggiungiamo 1 grado se c'è sweep (effetto diedro dello sweep)
    if sweep_deg > 0:
        dihedral_recommended_deg += 1.0

    new_state = state.with_derived(
        "lateral",
        Cl_beta=Cl_beta,
        Cn_beta=Cn_beta,
        V_V=V_V,
        twist_recommended_deg=twist_recommended_deg,
        dihedral_recommended_deg=dihedral_recommended_deg,
        dihedral_actual_deg=dihedral_deg
    )
    
    new_state = new_state.with_provenance(
        "lateral.Cl_beta", Provenance(source="4.6", kind=ProvenanceKind.ANALYTIC)
    )
    
    return new_state
import math
from rcsizer.core.state import DesignState, Provenance, ProvenanceKind

name = "stability_lateral"
version = "1.1.0"
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
    
    # FIX N2: Usa lo sweep calcolato dal modulo geometria (che gestisce sweep_c4)
    sweep_rad = geo.get("sweep_LE", 0.0)
    sweep_deg = sweep_rad * (180 / math.pi)
    
    dihedral_rad = inp.wing.panels[0].dihedral
    dihedral_deg = dihedral_rad * (180 / math.pi)
    
    taper = inp.wing.panels[0].chord_tip / inp.wing.panels[0].chord_root
    
    # 1. Dihedral Effect (Cl_beta)
    Cl_beta = - (CL_alpha * dihedral_rad / 4.0) * ((1 + 2*taper) / (3 * (1 + taper)))
    
    # 2. Weathercock Effect (Cn_beta) - FIX N1: Usa tail_scaled!
    tail_scaled = state.derived.get("tail_scaled", {})
    S_v = tail_scaled.get("S_v", 0.02)
    l_v = tail_scaled.get("l_v", 0.6)
    AR_v = inp.tail.AR_v or 2.0
    
    V_V = (S_v * l_v) / (S * b) if (S * b) > 0 else 0
    CL_alpha_v = (2 * math.pi * AR_v) / (2 + math.sqrt(4 + AR_v**2))
    eta_v = 0.9 
    Cn_beta = V_V * CL_alpha_v * eta_v
    
    # 3. Consigli
    twist_recommended_deg = 0.0
    if taper < 0.7 or sweep_deg > 2.0:
        twist_recommended_deg = -2.0
        if taper < 0.5 or sweep_deg > 5.0:
            twist_recommended_deg = -3.0
            
    dihedral_recommended_deg = 3.0 # Default per ala media
    if inp.wing.wing_position_z.value == "high":
        dihedral_recommended_deg = 2.0
    elif inp.wing.wing_position_z.value == "low":
        dihedral_recommended_deg = 4.0
        
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
    
    return new_state
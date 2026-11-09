import math
from rcsizer.core.state import DesignState, Provenance, ProvenanceKind
from rcsizer.core.presets import load_coefficients

name = "aero_datcom"
version = "3.0.0"
requires = ["input", "geometry", "airfoil", "atmosphere"]
provides = ["aero"]

def run(state: DesignState) -> DesignState:
    geo = state.derived["geometry"]
    af = state.derived["airfoil"]
    atm = state.derived["atmosphere"]
    mission = state.input.mission
    
    AR = geo["AR"]
    S = geo["S"]
    MAC = geo["MAC"]
    V = mission.V_cruise
    rho = atm["rho"]
    mu = atm["mu"]
    
    Re = (rho * V * MAC) / mu
    
    # Pendenza di portanza (DATCOM)
    cl_alpha_2d = 2 * math.pi * 0.9
    kappa = cl_alpha_2d / (2 * math.pi)
    M = V / atm["a_s"]
    beta = math.sqrt(1 - M**2) if M < 1.0 else 1.0
    CL_alpha = (2 * math.pi * AR) / (2 + math.sqrt(4 + ((AR * beta / kappa)**2)))
    
    CLmax_w = 0.9 * af["cl_max_2d"]
    
    # Resistenza (FIX P0 - D3)
    Cf_turb = 0.455 / (math.log10(Re)**2.58) if Re > 0 else 0.01
    Cf = Cf_turb # Rimosso il termine inutile -0.3/Re
    
    tc = af["thickness"]
    # Corretto: 0.6 / (x/c) = 2.0. Aggiunto max(1.0, ...) per la compressibilità
    mach_factor = max(1.0, 1.34 * (M**0.18)) if M > 0.2 else 1.0
    FF_wing = (1 + 2.0 * tc + 100 * (tc**4)) * mach_factor
    
    CD0_wing = (Cf * FF_wing * 1.0 * geo["S_wet"]) / S
    CD0_total = CD0_wing * 1.20 # Fattore per fusoliera e carrello
    
    # Fattore di Oswald
    coeffs = load_coefficients()
    e_oswald = coeffs["coefficients"]["e_oswald_raymer"]["value"]
    K = 1 / (math.pi * e_oswald * AR)
    
    W = state.derived.get("weights", {}).get("W", 15.0)
    Vs = math.sqrt((2 * W) / (rho * S * CLmax_w))
    
    new_state = state.with_derived(
        "aero",
        Re=Re, CL_alpha=CL_alpha, CLmax=CLmax_w,
        CD0=CD0_total, e_oswald=e_oswald, K=K,
        Vs=Vs, L_D_max=0.5 * math.sqrt(math.pi * e_oswald * AR / CD0_total)
    )
    return new_state
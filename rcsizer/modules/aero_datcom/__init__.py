import math
from rcsizer.core.state import DesignState, Provenance, ProvenanceKind
from rcsizer.core.presets import load_coefficients
from rcsizer.core.presets import load_coefficients
    

name = "aero_datcom"
version = "2.0.0"
coeffs = load_coefficients()
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
    
    # 1. NUMERO DI REYNOLDS
    Re = (rho * V * MAC) / mu
    
    # 2. PENDENZA DELLA CURVA DI PORTANZA (Sez 4.4 - DATCOM)
    cl_alpha_2d = 2 * math.pi * 0.9  # 0.9 correzione per Re bassi [E]
    kappa = cl_alpha_2d / (2 * math.pi)
    M = V / atm["a_s"]
    beta = math.sqrt(1 - M**2) if M < 1.0 else 1.0
    CL_alpha = (2 * math.pi * AR) / (2 + math.sqrt(4 + ((AR * beta / kappa)**2)))
    
    # 3. PORTANZA MASSIMA
    CLmax_w = 0.9 * af["cl_max_2d"]
    
    # 4. RESISTENZA (Component Build-up)
    # Cf laminare e turbolenta
    Cf_lam = 1.328 / math.sqrt(Re) if Re > 0 else 0.01
    Cf_turb = 0.455 / (math.log10(Re)**2.58) if Re > 0 else 0.01
    # Usiamo un Cf misto (transizione al 30%) [E]
    Cf = Cf_turb - (0.3 / Re) if Re > 0 else 0.01
    
    # Form Factor (FF) ala (Sez 4.4)
    tc = af["thickness"]
    FF_wing = (1 + 0.6 * tc + 100 * (tc**4)) * (1.34 * (M**0.18))
    
    # Resistenza parassita (CD0) dell'ala (solo ala per ora)
    # S_wet_w è calcolato nel WP1
    CD0_wing = (Cf * FF_wing * 1.0 * geo["S_wet"]) / S
    
    # Fattore di Oswald (Raymer) (Sez 4.4)
    
    e_oswald = coeffs["coefficients"]["e_oswald_raymer"]["value"]
    K = 1 / (math.pi * e_oswald * AR)
    
    # Aggiungiamo un 20% per fusoliera, carrello e interferenze [E]
    CD0_total = CD0_wing * 1.20
    
    # 5. VELOCITA' DI STALLO (usando il peso attuale)
    # Se weights.W non esiste ancora (prima iterazione), usiamo 10 Newton
    W = state.derived.get("weights", {}).get("W", 15.0)
    Vs = math.sqrt((2 * W) / (rho * S * CLmax_w))
    
    new_state = state.with_derived(
        "aero",
        Re=Re, CL_alpha=CL_alpha, CLmax=CLmax_w,
        CD0=CD0_total, e_oswald=e_oswald, K=K,
        Vs=Vs, L_D_max=0.5 * math.sqrt(math.pi * e_oswald * AR / CD0_total)
    )
    
    return new_state
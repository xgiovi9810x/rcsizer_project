import math
from rcsizer.core.state import DesignState

name = "performance_basic"
version = "2.0.0"
requires = ["input", "geometry", "aero", "weights", "atmosphere"]
provides = ["performance"]

def run(state: DesignState) -> DesignState:
    aero = state.derived["aero"]
    atm = state.derived["atmosphere"]
    geo = state.derived["geometry"]
    w = state.derived["weights"]
    inp = state.input
    
    V = inp.mission.V_cruise
    rho = atm["rho"]
    S = geo["S"]
    W = w["W"]
    
    # 1. Potenza richiesta in crociera (Sez. 4.10)
    # P_req = 0.5 * rho * V^3 * S * CD0 + (2 * K * W^2) / (rho * V * S)
    CD0 = aero["CD0"]
    K = aero["K"]
    
    term1 = 0.5 * rho * (V**3) * S * CD0
    term2 = (2 * K * (W**2)) / (rho * V * S) if (rho * V * S) > 0 else 0
    P_req = term1 + term2
    
    # 2. Calcolo Autonomia (FIX N5 - Endurance)
    # Leggiamo i dati della batteria dall'input
    batt = inp.propulsion.battery
    E_batt_Wh = batt.capacity_Ah * batt.voltage_nominal # Energia nominale in Watt-ora
    usable_E = E_batt_Wh * batt.usable_fraction
    
    endurance_h = 0.0
    if P_req > 0:
        endurance_h = usable_E / P_req
        
    # 3. Calcolo velocità ottimale per massima efficienza
    # V(L/D)max = sqrt( 2*(W/S) / (rho * sqrt(CD0/K)) )
    CL_star = math.sqrt(CD0 / K) if K > 0 else 0
    V_L_D_max = math.sqrt((2 * W) / (rho * S * CL_star)) if CL_star > 0 and rho * S > 0 else V

    new_state = state.with_derived(
        "performance",
        P_req=P_req,
        V_cruise=V,
        endurance_h=endurance_h,
        V_L_D_max=V_L_D_max
    )
    
    return new_state
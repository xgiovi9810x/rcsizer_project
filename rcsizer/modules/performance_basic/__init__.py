import math
from rcsizer.core.state import DesignState, Provenance, ProvenanceKind

name = "performance_basic"
version = "1.0.0"
requires = ["input", "geometry", "aero", "weights", "atmosphere"]
provides = ["performance"]

def run(state: DesignState) -> DesignState:
    aero = state.derived["aero"]
    atm = state.derived["atmosphere"]
    geo = state.derived["geometry"]
    w = state.derived["weights"]
    V = state.input.mission.V_cruise
    
    # Potenza richiesta (Sez 4.10)
    # P_req = 0.5 * rho * V^3 * S * CD0 + (2 * K * W^2) / (rho * V * S)
    term1 = 0.5 * atm["rho"] * (V**3) * geo["S"] * aero["CD0"]
    term2 = (2 * aero["K"] * (w["W"]**2)) / (atm["rho"] * V * geo["S"])
    P_req = term1 + term2
    
    new_state = state.with_derived(
        "performance",
        P_req=P_req,
        V_cruise=V
    )
    
    return new_state
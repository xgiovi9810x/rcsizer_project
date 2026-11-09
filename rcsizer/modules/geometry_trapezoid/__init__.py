import math
from rcsizer.core.state import DesignState

name = "geometry_trapezoid"
version = "5.0.0"
requires = ["input"]
provides = ["geometry", "atmosphere", "tail_scaled"]

def run(state: DesignState) -> DesignState:
    h = state.input.mission.altitude_ops
    T = 288.15 - 0.0065 * h
    rho = 1.225 * (T / 288.15)**4.2559
    mu = 1.458e-6 * (T**1.5) / (T + 110.4)
    a_s = math.sqrt(1.4 * 287.05 * T)
    
    wing_in = state.input.wing
    panel = wing_in.panels[0]
    W = state.derived.get("weights", {}).get("W", 15.0)
    
    S_target = W / wing_in.W_S_target
    b_target = math.sqrt(wing_in.AR_target * S_target)
    lam = panel.chord_tip / panel.chord_root
    c_r_target = (2 * S_target) / (b_target * (1 + lam))
    c_t_target = c_r_target * lam
    MAC = (2.0/3.0) * c_r_target * (1 + lam + lam**2) / (1 + lam)
    
    # FIX: L'ala parte dal 25% della fusoliera, non dal muso!
    L_f = state.input.fuselage.L_f
    x_LE_wing = state.input.fuselage.wing_position * L_f
    
    x_AC = x_LE_wing + 0.25 * MAC # Posizione reale dell'AC
    S_wet_w = S_target * (2 + 0.5 * 0.12)

    sweep_le = panel.sweep_LE if panel.sweep_LE is not None else 0.0

    tail_in = state.input.tail
    S_base = panel.span * (panel.chord_root + panel.chord_tip)
    scale_factor = S_target / S_base if S_base > 0 else 1.0
    
    S_h_target = (tail_in.S_h or 0.05) * scale_factor
    l_h_target = (tail_in.l_h or 0.6) * math.sqrt(scale_factor)
    S_v_target = (tail_in.S_v or 0.02) * scale_factor
    l_v_target = (tail_in.l_v or 0.6) * math.sqrt(scale_factor)

    new_state = state.with_derived(
        "atmosphere", T=T, rho=rho, mu=mu, a_s=a_s
    ).with_derived(
        "geometry", 
        S=S_target, b=b_target, MAC=MAC, AR=wing_in.AR_target, 
        x_AC=x_AC, S_wet=S_wet_w, c_r=c_r_target, c_t=c_t_target,
        sweep_LE=sweep_le, x_LE_wing=x_LE_wing
    ).with_derived(
        "tail_scaled", S_h=S_h_target, l_h=l_h_target, S_v=S_v_target, l_v=l_v_target
    )
    return new_state
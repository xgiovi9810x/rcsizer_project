import math
from rcsizer.core.state import DesignState

name = "geometry_trapezoid"
version = "4.1.0"
requires = ["input"]
provides = ["geometry", "atmosphere", "tail_scaled"]

def run(state: DesignState) -> DesignState:
    # --- 1. ATMOSFERA ---
    h = state.input.mission.altitude_ops
    T = 288.15 - 0.0065 * h
    rho = 1.225 * (T / 288.15)**4.2559
    mu = 1.458e-6 * (T**1.5) / (T + 110.4)
    a_s = math.sqrt(1.4 * 287.05 * T)
    
    # --- 2. OTTIMIZZAZIONE GEOMETRICA (Sizing) ---
    wing_in = state.input.wing
    panel = wing_in.panels[0]
    
    W = state.derived.get("weights", {}).get("W", 15.0)
    W_S_target = wing_in.W_S_target
    AR_target = wing_in.AR_target
    
    S_target = W / W_S_target
    b_target = math.sqrt(AR_target * S_target)
    
    lam = panel.chord_tip / panel.chord_root
    c_r_target = (2 * S_target) / (b_target * (1 + lam))
    c_t_target = c_r_target * lam
    
    MAC = (2.0/3.0) * c_r_target * (1 + lam + lam**2) / (1 + lam)
    x_AC = 0.25 * MAC
    S_wet_w = S_target * (2 + 0.5 * 0.12)

    # --- 3. GESTIONE SWEEP (FIX P0 - B3) ---
    sweep_le = panel.sweep_LE
    if sweep_le is None:
        if panel.sweep_c4 is not None:
            # Conversione da sweep al 25% a sweep al bordo d'attacco
            tan_sweep_le = math.tan(panel.sweep_c4) + (panel.chord_root / (2 * panel.span)) * (1 - lam)
            sweep_le = math.atan(tan_sweep_le)
        else:
            sweep_le = 0.0

    # --- 4. SCALATURA DELLA CODA (FIX P0 - B1) ---
    tail_in = state.input.tail
    S_base = panel.span * (panel.chord_root + panel.chord_tip)
    scale_factor = S_target / S_base if S_base > 0 else 1.0
    
    # Coda orizzontale
    S_h_orig = tail_in.S_h if tail_in.S_h else 0.05 
    l_h_orig = tail_in.l_h if tail_in.l_h else 0.6
    S_h_target = S_h_orig * scale_factor
    l_h_target = l_h_orig * math.sqrt(scale_factor)
    
    # Coda verticale (FIX P0 - B1: ora viene scalata!)
    S_v_orig = tail_in.S_v if tail_in.S_v else 0.02
    l_v_orig = tail_in.l_v if tail_in.l_v else 0.6
    S_v_target = S_v_orig * scale_factor
    l_v_target = l_v_orig * math.sqrt(scale_factor)

    new_state = state.with_derived(
        "atmosphere", T=T, rho=rho, mu=mu, a_s=a_s
    ).with_derived(
        "geometry", 
        S=S_target, b=b_target, MAC=MAC, AR=AR_target, 
        x_AC=x_AC, S_wet=S_wet_w, c_r=c_r_target, c_t=c_t_target,
        sweep_LE=sweep_le # Salva lo sweep calcolato
    ).with_derived(
        "tail_scaled",
        S_h=S_h_target, l_h=l_h_target,
        S_v=S_v_target, l_v=l_v_target # Aggiunte le code verticali
    )
    
    return new_state
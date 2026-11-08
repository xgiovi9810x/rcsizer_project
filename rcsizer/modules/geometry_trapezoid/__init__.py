import math
from rcsizer.core.state import DesignState

name = "geometry_trapezoid"
version = "4.0.0"
requires = ["input"]
provides = ["geometry", "atmosphere"]

def run(state: DesignState) -> DesignState:
    # --- 1. ATMOSFERA (Sez. 4.1) ---
    h = state.input.mission.altitude_ops
    T = 288.15 - 0.0065 * h
    rho = 1.225 * (T / 288.15)**4.2559
    mu = 1.458e-6 * (T**1.5) / (T + 110.4)
    a_s = math.sqrt(1.4 * 287.05 * T)
    
    # --- 2. OTTIMIZZAZIONE GEOMETRICA (Sizing) ---
    wing_in = state.input.wing
    panel = wing_in.panels[0] # Prendiamo il pannello base come riferimento
    
    # Peso dall'iterazione precedente (se esiste), altrimenti stima iniziale
    W = state.derived.get("weights", {}).get("W", 15.0)
    
    # Target di progetto
    W_S_target = wing_in.W_S_target
    AR_target = wing_in.AR_target
    
    # Calcolo Area e Apertura necessari
    S_target = W / W_S_target
    b_target = math.sqrt(AR_target * S_target)
    
    # Manteniamo la rastremazione originale (taper ratio)
    lam = panel.chord_tip / panel.chord_root
    
    # Ricalcolo Corde per far tornare l'Area
    # S = b * (c_r + c_t) / 2  -->  S = b * c_r * (1 + lam) / 2
    c_r_target = (2 * S_target) / (b_target * (1 + lam))
    c_t_target = c_r_target * lam
    
    # Calcolo MAC e x_AC (assumiamo sweep = 0 per semplicità)
    MAC = (2.0/3.0) * c_r_target * (1 + lam + lam**2) / (1 + lam)
    x_AC = 0.25 * MAC # Approssimazione: AC al 25% della MAC
    
    # Superficie bagnata
    S_wet_w = S_target * (2 + 0.5 * 0.12)

    # --- 3. SCALATURA DELLA CODA (manteniamo il volume V_H costante) ---
    tail_in = state.input.tail
    # Area originale della coda nel JSON
    S_h_orig = tail_in.S_h if tail_in.S_h else 0.05 
    l_h = tail_in.l_h if tail_in.l_h else 0.6
    
    # Calcoliamo l'area alare originale del JSON base
    S_base = panel.span * (panel.chord_root + panel.chord_tip)
    
    # Scaliamo l'area della coda in proporzione alla nuova ala
    S_h_target = S_h_orig * (S_target / S_base)
    
    # Scaliamo anche il braccio di leva (se la fusoliera cresce)
    l_h_target = l_h * math.sqrt(S_target / S_base)

    new_state = state.with_derived(
        "atmosphere", T=T, rho=rho, mu=mu, a_s=a_s
    ).with_derived(
        "geometry", 
        S=S_target, 
        b=b_target, 
        MAC=MAC, 
        AR=AR_target, 
        x_AC=x_AC, 
        S_wet=S_wet_w,
        c_r=c_r_target,
        c_t=c_t_target
    ).with_derived(
        "tail_scaled",
        S_h=S_h_target,
        l_h=l_h_target
    )
    
    return new_state
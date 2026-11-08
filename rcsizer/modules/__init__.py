"""Moduli M1–M9 (vuoti in WP0; popolati nei WP1–WP9)."""
from rcsizer.core.state import DesignState

name = "weights_table"
version = "3.0.0"
requires = ["input", "geometry", "structure", "stability"]
provides = ["weights"]

def run(state: DesignState) -> DesignState:
    geo = state.derived["geometry"]
    struct = state.derived.get("structure", {})
    inp = state.input
    
    # --- 1. MASSA STRUTTURALE (dal modulo structure) ---
    # Usiamo .get(..., 0.0) per evitare crash se un dato manca
    m_wing = struct.get("m_wing", 0.0)
    m_tail = struct.get("m_tail", 0.0)
    m_carb_tube = struct.get("m_carb_tube", 0.0)
    m_struct = m_wing + m_tail + m_carb_tube
    
    # --- 2. MASSA COMPONENTI ---
    m_motor = inp.propulsion.motor.mass
    m_batt = inp.propulsion.battery.mass
    m_esc = inp.propulsion.ESC_mass
    m_rx = inp.propulsion.receiver_mass
    
    m_servos = 0.0
    if inp.propulsion.servos:
        m_servos = inp.propulsion.servos.count * inp.propulsion.servos.mass_each
        
    m_comp = m_motor + m_batt + m_esc + m_rx + m_servos
    
    # --- 3. MASSA TOTALE E PESO (W) ---
    m_tot = m_struct + m_comp
    W = m_tot * 9.81
    
    # --- 4. CALCOLO DEL CG (Somma dei Momenti) ---
    # Assumiamo che i componenti (motore, batteria, ecc.) siano raggruppati nel muso (x = 0.0)
    # La struttura (ala e coda) ha il suo CG vicino al 25% della MAC.
    # (Nota: x è la distanza dal muso dell'aereo)
    
    x_cg_comp = 0.0
    # Approssimiamo il CG strutturale al 25% della MAC dell'ala
    x_cg_struct = geo.get("x_AC", 0.0) + 0.25 * geo["MAC"]
    
    # Formula del baricentro: (m1*x1 + m2*x2) / (m1 + m2)
    x_cg = 0.0
    if m_tot > 0:
        x_cg = (m_struct * x_cg_struct + m_comp * x_cg_comp) / m_tot
        
    # --- 5. CALCOLO h_cg (Frazione di MAC) ---
    # Troviamo il bordo d'attacco della MAC
    x_le_mac = geo.get("x_AC", 0.0) - 0.25 * geo["MAC"]
    
    h_cg = 0.0
    if geo["MAC"] > 0:
        h_cg = (x_cg - x_le_mac) / geo["MAC"]
    
    # --- 6. AGGIORNAMENTO DELLO STATO ---
    new_state = state.with_derived(
        "weights",
        m_tot=m_tot,
        W=W,
        m_struct=m_struct,
        m_comp=m_comp,
        x_cg=x_cg,
        h_cg=h_cg
    )
    
    return new_state
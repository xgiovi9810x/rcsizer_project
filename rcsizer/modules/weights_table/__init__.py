from rcsizer.core.state import DesignState

name = "weights_table"
version = "7.0.0"
requires = ["input", "geometry", "structure", "stability"]
provides = ["weights"]

def run(state: DesignState) -> DesignState:
    geo = state.derived["geometry"]
    struct = state.derived.get("structure", {})
    stab = state.derived.get("stability", {})
    inp = state.input
    
    # --- 1. MASSE ---
    m_wing = struct.get("m_wing", 0.0)
    m_tail = struct.get("m_tail", 0.0)
    m_carb = struct.get("m_carb_tube", 0.0)
    m_struct = m_wing + m_tail + m_carb
    
    m_motor = inp.propulsion.motor.mass
    m_batt = inp.propulsion.battery.mass
    m_esc = inp.propulsion.ESC_mass
    m_rx = inp.propulsion.receiver_mass
    m_wiring = inp.propulsion.wiring_mass
    m_gear = inp.propulsion.landing_gear_mass
    m_payload = inp.mission.payload_mass
    
    m_servos = 0.0
    if inp.propulsion.servos:
        m_servos = inp.propulsion.servos.count * inp.propulsion.servos.mass_each
        
    m_comp = m_motor + m_batt + m_esc + m_rx + m_wiring + m_gear + m_payload + m_servos
    m_tot = m_struct + m_comp
    W = m_tot * 9.81
    
    # --- 2. POSIZIONI (Datum: Muso dell'aereo a x=0) ---
    x_motor = inp.propulsion.motor.x_pos
    x_batt = inp.propulsion.battery.x_pos
    
    x_servos = 0.25
    if inp.propulsion.servos:
        x_servos = inp.propulsion.servos.x_pos
        
    x_esc = x_motor + 0.02 # Appena dietro il motore
    x_rx = x_servos        # Insieme ai servi
    x_payload = geo.get("x_LE_wing", 0.2) # Payload sull'ala
    
    # Struttura (Ala, coda, tubo)
    x_cg_struct = geo.get("x_AC", 0.2) 
    
    # --- 3. CALCOLO CG ATTUALE ---
    momenti = (
        (m_motor * x_motor) + (m_batt * x_batt) + 
        (m_servos * x_servos) + (m_payload * x_payload) +
        (m_esc * x_esc) + (m_rx * x_rx) + (m_gear * x_motor) + 
        (m_struct * x_cg_struct)
    )
    x_cg = momenti / m_tot if m_tot > 0 else 0
    
    x_le_mac = geo.get("x_LE_wing", 0.2)
    h_cg = (x_cg - x_le_mac) / geo["MAC"] if geo["MAC"] > 0 else 0
    
    # --- 4. SUGGERIMENTO POSIZIONE BATTERIA (Balancing Act) ---
    h_cg_target = stab.get("h_cg_target", h_cg)
    x_cg_target = x_le_mac + (h_cg_target * geo["MAC"])
    
    # Calcoliamo il momento di tutto TRANNE la batteria
    momenti_senza_batt = momenti - (m_batt * x_batt)
    
    # Equazione: x_cg_target = (momenti_senza_batt + m_batt * x_batt_opt) / m_tot
    # Risolviamo per x_batt_opt:
    x_batt_suggested = 0.0
    if m_batt > 0:
        x_batt_suggested = (x_cg_target * m_tot - momenti_senza_batt) / m_batt
        
    # Verifichiamo se la posizione suggerita è fisicamente possibile (tra 0 e la lunghezza fusoliera)
    L_f = inp.fuselage.L_f
    is_batt_valid = 0.0 <= x_batt_suggested <= L_f
    
    # Calcoliamo di quanto si deve spostare
    delta_x_batt = x_batt_suggested - x_batt
    
    new_state = state.with_derived(
        "weights", 
        m_tot=m_tot, W=W, m_struct=m_struct, m_comp=m_comp, 
        x_cg=x_cg, h_cg=h_cg,
        x_batt_suggested=x_batt_suggested,
        is_batt_valid=bool(is_batt_valid),
        delta_x_batt=delta_x_batt
    )
    return new_state
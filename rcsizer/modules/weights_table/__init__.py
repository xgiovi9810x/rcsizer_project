from rcsizer.core.state import DesignState

name = "weights_table"
version = "5.0.0"
requires = ["input", "geometry", "structure", "stability"]
provides = ["weights"]

def run(state: DesignState) -> DesignState:
    geo = state.derived["geometry"]
    struct = state.derived.get("structure", {})
    inp = state.input
    
    # 1. Massa Strutturale (FIX P1 - B2: aggiunto il carbonio)
    m_wing = struct.get("m_wing", 0.0)
    m_tail = struct.get("m_tail", 0.0)
    m_carb = struct.get("m_carb_tube", 0.0)
    m_struct = m_wing + m_tail + m_carb
    
    # 2. Massa Componenti (FIX P1 - B2: aggiunti tutti i campi)
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
    
    # 3. Massa Totale
    m_tot = m_struct + m_comp
    W = m_tot * 9.81
    
    # 4. Calcolo CG (FIX P1 - B5: uso coordinate sensate)
    x_motor = 0.05
    x_batt = 0.15
    x_servos = 0.25
    x_payload = 0.25
    
    x_cg_struct = geo.get("x_AC", 0.0) + 0.25 * geo["MAC"]
    
    momenti = (
        (m_motor * x_motor) + (m_batt * x_batt) + 
        (m_servos * x_servos) + (m_payload * x_payload) +
        (m_esc * x_motor) + (m_rx * x_servos) + 
        (m_struct * x_cg_struct)
    )
    x_cg = momenti / m_tot if m_tot > 0 else 0
    
    x_le_mac = geo.get("x_AC", 0.0) - 0.25 * geo["MAC"]
    h_cg = (x_cg - x_le_mac) / geo["MAC"] if geo["MAC"] > 0 else 0
    
    new_state = state.with_derived(
        "weights", m_tot=m_tot, W=W, m_struct=m_struct, m_comp=m_comp, x_cg=x_cg, h_cg=h_cg
    )
    return new_state
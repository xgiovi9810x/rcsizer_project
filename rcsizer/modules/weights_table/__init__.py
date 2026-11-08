from rcsizer.core.state import DesignState, Provenance, ProvenanceKind

name = "weights_table"
version = "2.0.0"
requires = ["input", "geometry", "structure", "stability", "aero"]
provides = ["weights"]

def run(state: DesignState) -> DesignState:
    geo = state.derived["geometry"]
    struct = state.derived["structure"]
    inp = state.input
    
    # 1. Massa Strutturale (dal modulo structure)
    m_wing = struct["m_wing"]
    m_tail = struct["m_tail"]
    m_struct = m_wing + m_tail
    
    # 2. Massa Componenti
    m_motor = inp.propulsion.motor.mass
    m_batt = inp.propulsion.battery.mass
    m_esc = inp.propulsion.ESC_mass
    m_rx = inp.propulsion.receiver_mass
    
    # 3. Massa Totale e Peso (W)
    m_tot = m_struct + m_motor + m_batt + m_esc + m_rx
    W = m_tot * 9.81
    
    # 4. Calcolo del CG (Somma dei Momenti)
    # Assumiamo che i componenti siano tutti nel muso (x = 0.0)
    # L'ala e la struttura hanno il loro CG a x_cg_struct
    x_cg_struct = geo["x_AC"] + 0.25 * geo["MAC"] # Stima: 25% della MAC
    x_cg_comp = 0.0 # Muso
    
    x_cg = (m_struct * x_cg_struct + (m_motor + m_batt + m_esc + m_rx) * x_cg_comp) / m_tot if m_tot > 0 else 0
    
    # Calcolo h_cg (frazione di MAC)
    # Assumiamo che x_LE_MAC sia x_AC - 0.25*MAC
    x_le_mac = geo["x_AC"] - 0.25 * geo["MAC"]
    h_cg = (x_cg - x_le_mac) / geo["MAC"] if geo["MAC"] > 0 else 0
    
    new_state = state.with_derived(
        "weights",
        m_tot=m_tot,
        W=W,
        x_cg=x_cg,
        h_cg=h_cg
    )
    
    return new_state
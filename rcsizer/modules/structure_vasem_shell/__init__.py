import math
from rcsizer.core.state import DesignState

name = "structure_vasem_shell"
version = "5.1.0"
requires = ["input", "geometry", "airfoil"]
provides = ["structure"]

def run(state: DesignState) -> DesignState:
    geo = state.derived["geometry"]
    mat = state.input.material
    proc = state.input.print_process
    mission = state.input.mission
    wing = state.input.wing
    
    w_dict = state.derived.get("weights", {})
    W = w_dict.get("W", 15.0)
    
    af_dict = state.derived.get("airfoil", {})
    t_c = af_dict.get("thickness", 0.12)
    
    n_limit = mission.n_limit_target
    FOS = 2.0
    b = geo["b"]
    MAC = geo["MAC"]
    h_max = t_c * MAC 
    
    M_root = (n_limit * W * b) / 8.0
    V_root = (n_limit * W) / 2.0
    
    I_carb = 0.0
    M_carb = 0.0
    m_carb_tube = 0.0
    
    if wing.internal_structure and wing.internal_structure.carbon_tube_outer_d > 0:
        D_out = wing.internal_structure.carbon_tube_outer_d
        D_in = wing.internal_structure.carbon_tube_inner_d
        I_carb = (math.pi / 64.0) * (D_out**4 - D_in**4)
        
        A_tube = (math.pi / 4.0) * (D_out**2 - D_in**2)
        m_carb_tube = A_tube * b * 1600.0
        
        E_carb = 70e9 
        I_skin_equiv = (math.pi * proc.w_e * (h_max**3)) / 4.0
        E_skin = mat.E_xy
        
        stiffness_carb = E_carb * I_carb
        stiffness_skin = E_skin * I_skin_equiv
        total_stiffness = stiffness_carb + stiffness_skin
        
        if total_stiffness > 0:
            M_carb = M_root * (stiffness_carb / total_stiffness)
    
    M_skin = M_root - M_carb
    
    I_skin_equiv = (math.pi * proc.w_e * (h_max**3)) / 4.0
    sigma_applied = (M_skin * (h_max / 2.0)) / I_skin_equiv if I_skin_equiv > 0 else 0
    sigma_allow = mat.sigma_y_xy * 0.5 
    MS_strength = (sigma_allow / (FOS * sigma_applied)) - 1.0 if sigma_applied > 0 else 999
    
    k_c = 4.0
    nu = mat.nu
    if sigma_applied > 0:
        sigma_target = sigma_applied * FOS
        b_max_buckling = proc.w_e * math.sqrt((k_c * math.pi**2 * mat.E_xy) / (12 * (1 - nu**2) * sigma_target))
    else:
        b_max_buckling = 0.1
        
    tau_applied = V_root / (proc.w_e * h_max) if h_max > 0 else 0
    tau_allow = mat.sigma_y_z * 0.5
    MS_delam = (tau_allow / (FOS * tau_applied)) - 1.0 if tau_applied > 0 else 999
    
    A_wall_outer = (2 * MAC * 1.1) * b
    m_outer_skin = mat.rho_filament * A_wall_outer * proc.w_e
    
    actual_spacing = max(b_max_buckling, 0.015) 
    N_bays = b / actual_spacing
    N_ribs = N_bays + 1
    
    V_ribs = N_ribs * (MAC * h_max * proc.w_e)
    L_diag = math.sqrt(actual_spacing**2 + h_max**2)
    V_diag = N_bays * 2 * (L_diag * proc.w_e * h_max) 
    
    m_truss = (V_ribs + V_diag) * mat.rho_filament
    m_wing_total = m_outer_skin + m_truss
    m_tail = m_wing_total * 0.15 
    
    new_state = state.with_derived(
        "structure",
        m_wing=m_wing_total,
        m_carb_tube=m_carb_tube,
        m_tail=m_tail,
        m_truss=m_truss,
        t_w=proc.w_e,
        M_root=M_root,
        M_carb=M_carb,
        sigma_applied=sigma_applied,
        MS_strength=MS_strength,
        MS_buckling=MS_delam, 
        rib_spacing_max_mm=round(actual_spacing * 1000, 1),
        delamination_safe=bool(MS_delam > 0) # <-- FIX
    )
    
    return new_state
from rcsizer.core.state import DesignState
import math

name = "export_params_table"
version = "4.0.0"
requires = ["input", "geometry", "aero", "stability", "lateral", "structure", "weights", "performance", "constraints"]
provides = ["export"]

def run(state: DesignState) -> DesignState:
    geo = state.derived["geometry"]
    w = state.derived["weights"]
    stab = state.derived["stability"]
    struct = state.derived.get("structure", {})
    aero = state.derived["aero"]
    perf = state.derived.get("performance", {})
    cons = state.derived.get("constraints", {})
    lat = state.derived.get("lateral", {})
    
    # FIX P0 - B3: uso .get() per evitare crash se sweep_LE è None
    sweep_le_deg = 0.0
    if "sweep_LE" in geo:
        sweep_le_deg = geo["sweep_LE"] * (180/math.pi)
    elif state.input.wing.panels[0].sweep_LE is not None:
        sweep_le_deg = state.input.wing.panels[0].sweep_LE * (180/math.pi)
    
    cad_params = {
        "Ala": {
            "Apertura_b_mm": round(geo["b"] * 1000, 1),
            "Corda_Radice_mm": round(geo.get("c_r", 0) * 1000, 1),
            "Corda_Punta_mm": round(geo.get("c_t", 0) * 1000, 1),
            "MAC_mm": round(geo["MAC"] * 1000, 1),
            "Freccia_LE_gradi": round(sweep_le_deg, 1),
            "Diedro_Attuale_gradi": round(lat.get("dihedral_actual_deg", 0.0), 1),
            "Diedro_Consigliato_gradi": round(lat.get("dihedral_recommended_deg", 0.0), 1),
            "Svergolamento_Consigliato_gradi": round(lat.get("twist_recommended_deg", 0.0), 1),
            "Spaziatura_Max_Centine_mm": struct.get("rib_spacing_max_mm", 0)
        },
        "Impennaggi": {
            "Area_Coda_Orizzontale_mm2": round(stab.get("S_h", 0) * 1e6, 1),
            "Braccio_Coda_Orizz_mm": round(stab.get("l_h", 0) * 1000, 1),
        },
        "Stampa_3D": {
            "Spessore_Parete_mm": round(struct.get("t_w", 0) * 1000, 2),
            "Nozzle_mm": round(state.input.print_process.nozzle * 1000, 2),
            "Layer_Height_mm": round(state.input.print_process.layer_h * 1000, 2),
        },
        "Bilanciamento": {
            "CG_Target_mm_dal_LE": round(stab["h_cg_target"] * geo["MAC"] * 1000, 1),
            "Margine_Statico_Percentuale": round((stab["h_n"] - stab["h_cg_target"]) * 100, 1),
        }
    }
    
    report = {
        "Riepilogo": {
            "Peso_Totale_g": round(w["m_tot"] * 1000, 1),
            "Carico_Alare_g_dm2": round((w["m_tot"] * 1000) / (geo["S"] * 100), 1),
            "Velocita_Stallo_kmh": round(aero["Vs"] * 3.6, 1),
            "Efficienza_Massima_L_D": round(aero.get("L_D_max", 0), 1),
            "Potenza_Crociera_W": round(perf.get("P_req", 0), 1)
        },
        "Verifiche_Strutturali": {
            "Sforzo_Applicato_MPa": round(struct.get("sigma_applied", 0) / 1e6, 2),
            "Margine_Resistenza": round(struct.get("MS_strength", 0), 2),
            "Margine_Buckling": round(struct.get("MS_buckling", 0), 2),
            "Margine_Delaminazione": round(struct.get("MS_delam", 0), 2),
            "Massa_Guscio_e_Reticolo_g": round(struct.get("m_wing", 0) * 1000, 1),
            "Massa_Tubo_Carbonio_g": round(struct.get("m_carb_tube", 0.0) * 1000, 1)
        },
        "Verifiche_Stabilita": {
            "Cl_beta_Effetto_Diedro": round(lat.get("Cl_beta", 0.0), 4),
            "Cn_beta_Effetto_Banderuola": round(lat.get("Cn_beta", 0.0), 4),
            "Volume_Coda_Verticale_V_V": round(lat.get("V_V", 0.0), 3)
        },
        "Vincoli_Progetto": {
            "Progetto_Valido": bool(cons.get("is_valid", True)),
            "Violazioni": cons.get("violations", []),
            "Consigli": cons.get("advices", [])
        }
    }
    
    new_state = state.with_derived("export", cad_parameters=cad_params, report=report, success=True)
    return new_state
from rcsizer.core.state import DesignState
import math

name = "export_params_table"
version = "5.0.0"
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
    inp = state.input
    
    # Calcoli per impennaggi
    tail = inp.tail
    tail_scaled = state.derived.get("tail_scaled", {})
    S_h = tail_scaled.get("S_h", 0.05)
    AR_h = tail.AR_h or 4.0
    b_h = math.sqrt(S_h * AR_h)
    
    S_v = tail_scaled.get("S_v", 0.02)
    AR_v = tail.AR_v or 2.0
    h_v = math.sqrt(S_v * AR_v)

    cad_params = {
        "Ala": {
            "Apertura_b_mm": round(geo["b"] * 1000, 1),
            "Corda_Radice_mm": round(geo.get("c_r", 0) * 1000, 1),
            "Corda_Punta_mm": round(geo.get("c_t", 0) * 1000, 1),
            "MAC_mm": round(geo["MAC"] * 1000, 1),
            "Freccia_LE_gradi": round(geo.get("sweep_LE", 0.0) * (180/math.pi), 1),
            "Diedro_Consigliato_gradi": round(lat.get("dihedral_recommended_deg", 0.0), 1),
            "Svergolamento_Consigliato_gradi": round(lat.get("twist_recommended_deg", 0.0), 1),
            "Spaziatura_Max_Centine_mm": struct.get("rib_spacing_max_mm", 0)
        },
        "Fusoliera": {
            "Lunghezza_L_f_mm": round(inp.fuselage.L_f * 1000, 1),
            "Posizione_Ala_dal_Muso_mm": round(inp.fuselage.wing_position * inp.fuselage.L_f * 1000, 1),
            "Larghezza_Max_mm": round(max(sec.width for sec in inp.fuselage.sections) * 1000, 1),
            "Altezza_Max_mm": round(max(sec.height for sec in inp.fuselage.sections) * 1000, 1)
        },
        "Coda_Orizzontale": {
            "Area_mm2": round(S_h * 1e6, 1),
            "Apertura_mm": round(b_h * 1000, 1),
            "Braccio_l_h_mm": round(tail_scaled.get("l_h", 0) * 1000, 1),
            "Corda_Radice_Stimata_mm": round((S_h / (b_h * 0.8)) * 1000, 1) # Stima grezza per AR
        },
        "Coda_Verticale": {
            "Area_mm2": round(S_v * 1e6, 1),
            "Altezza_mm": round(h_v * 1000, 1),
            "Braccio_l_v_mm": round(tail_scaled.get("l_v", 0) * 1000, 1)
        },
        "Stampa_3D": {
            "Spessore_Parete_mm": round(struct.get("t_w", 0) * 1000, 2),
            "Nozzle_mm": round(inp.print_process.nozzle * 1000, 2),
            "Layer_Height_mm": round(inp.print_process.layer_h * 1000, 2),
        },
        "Bilanciamento": {
            "CG_Target_mm_dal_LE": round(stab["h_cg_target"] * geo["MAC"] * 1000, 1),
            "Posizione_Batteria_Suggerita_mm": round(w.get("x_batt_suggested", 0) * 1000, 1),
        }
    }
    
    report = {
        "Riepilogo": {
            "Peso_Totale_g": round(w["m_tot"] * 1000, 1),
            "Velocita_Stallo_kmh": round(aero["Vs"] * 3.6, 1),
            "Autonomia_min": round(perf.get("endurance_h", 0) * 60, 1),
            "Potenza_Crociera_W": round(perf.get("P_req", 0), 1)
        },
        "Vincoli_Progetto": {
            "Progetto_Valido": bool(cons.get("is_valid", True)),
            "Violazioni": cons.get("violations", []),
            "Consigli": cons.get("advices", [])
        }
    }
    
    new_state = state.with_derived("export", cad_parameters=cad_params, report=report, success=True)
    return new_state
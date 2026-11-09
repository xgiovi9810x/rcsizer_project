import streamlit as st
import math
from rcsizer.core.loader import load_design
from rcsizer.core.pipeline import Pipeline
from rcsizer.core.registry import ModuleRegistry
from pathlib import Path

# Configurazione della pagina
st.set_page_config(page_title="RCSizer", page_icon="✈️", layout="wide")

st.title("✈️ RCSizer - Preliminary Sizing Tool")
st.markdown("Inserisci i parametri nella barra laterale per ottimizzare il tuo aeromodello stampato in 3D.")

# --- SIDEBAR: INPUT UTENTE ---
with st.sidebar:
    st.header("1. Missione")
    V_cruise = st.number_input("Velocità di Crociera (m/s)", value=15.0, step=1.0)
    altitude = st.number_input("Quota Operativa (m)", value=100.0)
    n_limit = st.slider("Fattore di Carico (G)", min_value=2.0, max_value=10.0, value=4.5)
    
    st.header("2. Ala (Target)")
    W_S_target = st.slider("Carico Alare Target (N/m²)", min_value=20.0, max_value=120.0, value=45.0)
    AR_target = st.slider("Allungamento (AR Target)", min_value=3.0, max_value=10.0, value=6.0)
    airfoil = st.text_input("Profilo Alare (es. NACA2412)", value="NACA2412")
    
    st.header("3. Struttura e Stampa")
    w_e = st.number_input("Larghezza Estrusione w_e (mm)", value=0.45, step=0.05) / 1000.0
    carbon_outer = st.number_input("Tubo Carbonio Diam. Esterno (mm)", value=10.0, step=1.0) / 1000.0
    carbon_inner = st.number_input("Tubo Carbonio Diam. Interno (mm)", value=8.0, step=1.0) / 1000.0
    
    st.header("4. Pesi e Bilanciamento")
    m_motor = st.number_input("Massa Motore (g)", value=150.0) / 1000.0
    m_batt = st.number_input("Massa Batteria (g)", value=180.0) / 1000.0
    x_batt = st.number_input("Posizione Batteria dal muso (mm)", value=350.0) / 1000.0
    
    # Bottone di esecuzione
    run_btn = st.button("🚀 Esegui Dimensionamento", use_container_width=True)


# --- MAIN AREA: ESECUZIONE E RISULTATI ---
if run_btn:
    # Costruiamo il dizionario di input (uguale al JSON)
    input_data = {
        "aircraft_type": "trainer",
        "mission": {
            "V_cruise": V_cruise, "altitude_ops": altitude, 
            "takeoff_mode": "hand_launch", "n_limit_target": n_limit,
        },
        "wing": {
            "panels": [{
                "span": 0.781, "chord_root": 0.2565, "chord_tip": 0.24,
                "sweep_LE": 0.0, "airfoil_root": airfoil, "airfoil_tip": airfoil,
            }],
            "W_S_target": W_S_target, "AR_target": AR_target,
            "internal_structure": {
                "carbon_tube_outer_d": carbon_outer, "carbon_tube_inner_d": carbon_inner, "truss_angle": 0.7854
            }
        },
        "tail": {
            "tail_config": "conventional", "S_h": 0.0774, "l_h": 0.6477, "AR_h": 4.0,
            "S_v": 0.0258, "l_v": 0.6477, "AR_v": 2.0
        },
        "fuselage": {
            "L_f": 0.876,
            "sections": [{"x": 0.0, "width": 0.1, "height": 0.12}, {"x": 0.876, "width": 0.05, "height": 0.06}],
            "wing_position": 0.25, "tail_position": 0.8
        },
        "material": "pla",
        "print_process": {
            "nozzle": 0.0004, "w_e": w_e, "layer_h": 0.0002, "build_volume": [0.22, 0.22, 0.25]
        },
        "propulsion": {
            "motor": {"P_max": 500.0, "mass": m_motor, "x_pos": 0.05},
            "battery": {"cells_S": 3, "cells_P": 1, "capacity_Ah": 2.2, "voltage_nominal": 11.1, "mass": m_batt, "C_rate_max": 30.0, "x_pos": x_batt},
            "ESC_mass": 0.04, "receiver_mass": 0.02
        }
    }

    # Esecuzione del motore
    with st.spinner("Calcolo in corso..."):
        try:
            # 1. Validazione
            schema = load_design(input_data)
            
            # 2. Pipeline
            registry = ModuleRegistry()
            registry.discover()
            pipeline_path = Path("rcsizer/config/pipeline.yaml")
            pipeline = Pipeline.from_file(registry, pipeline_path)
            
            final_state = pipeline.run(schema)
            
            # 3. Estrazione risultati
            d = final_state.derived
            geo = d["geometry"]
            w = d["weights"]
            aero = d["aero"]
            stab = d["stability"]
            struct = d["structure"]
            cons = d["constraints"]
            
            # --- LAYOUT A COLONNE ---
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Peso Totale", f"{w['m_tot']*1000:.1f} g")
            col2.metric("Area Alare", f"{geo['S']:.3f} m²")
            col3.metric("Apertura", f"{geo['b']*1000:.0f} mm")
            col4.metric("Vel. Stallo", f"{aero['Vs']*3.6:.1f} km/h")

            st.divider()

            # --- STABILITA' ---
            st.subheader("Stabilità e Bilanciamento")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Neutral Point", f"{stab['h_n']*100:.1f} % MAC")
            col_b.metric("CG Target", f"{stab['h_cg_target']*100:.1f} % MAC")
            
            # Colora il margine statico in base al valore
            sm_val = stab['SM'] * 100
            sm_color = "normal" if 5.0 <= sm_val <= 20.0 else "inverse"
            col_c.metric("Margine Statico", f"{sm_val:.1f} %", delta=f"{sm_val - 12:.1f}% vs target", delta_color=sm_color)

            # Consiglio Batteria
            if w.get("x_batt_suggested", 0) > 0:
                st.info(f"💡 **Consiglio:** Per centrare il CG, sposta la batteria a **{w['x_batt_suggested']*1000:.0f} mm** dal muso (attualmente {x_batt*1000:.0f} mm).")

            st.divider()

            # --- STRUTTURA ---
            st.subheader("Verifiche Strutturali")
            col_d, col_e, col_f = st.columns(3)
            
            ms_s = struct['MS_strength']
            ms_b = struct['MS_buckling']
            
            col_d.metric("Resistenza", f"{ms_s:.2f}", delta="Sicuro" if ms_s > 0 else "Rischio Rottura", delta_color="normal" if ms_s > 0 else "inverse")
            col_e.metric("Buckling", f"{ms_b:.2f}", delta="Sicuro" if ms_b > 0 else "Rischio Schiacciamento", delta_color="normal" if ms_b > 0 else "inverse")
            col_f.metric("Spaziatura Centine", f"{struct['rib_spacing_max_mm']:.1f} mm")

            st.divider()

            # --- VERDETTO FINALE ---
            st.subheader("Verdetto Finale")
            if cons["is_valid"]:
                st.success("✅ **PROGETTO VALIDO!** L'aereo è bilanciato e sicuro.")
            else:
                st.error("❌ **PROGETTO NON VALIDO!** Ci sono problemi critici da risolvere.")
                
            for v in cons["violations"]:
                st.warning(f"⚠️ {v}")
            for a in cons["advices"]:
                st.write(f"👉 {a}")

        except Exception as e:
            st.error(f"Errore durante il calcolo: {e}")
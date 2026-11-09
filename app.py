import streamlit as st
import math
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

# Import del core
from rcsizer.core.loader import load_design
from rcsizer.core.pipeline import Pipeline
from rcsizer.core.registry import ModuleRegistry

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="RCSizer Dashboard", page_icon="✈️", layout="wide")

# --- FUNZIONI DI SUPPORTO ---
def plot_wing_planform(span, root_chord, tip_chord, sweep_deg):
    """Genera un grafico Plotly della pianta dell'ala (vista dall'alto)."""
    sweep_rad = math.radians(sweep_deg)
    semi_span = span / 2.0
    
    # Coordinate ala destra
    x_right = [0, semi_span, semi_span, 0, 0]
    y_right = [0, semi_span * math.tan(sweep_rad), semi_span * math.tan(sweep_rad) + tip_chord, root_chord, 0]
    
    # Coordinate ala sinistra (specchiate)
    x_left = [-x for x in x_right]
    y_left = y_right

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_right, y=y_right, fill='toself', mode='lines', name='Ala Destra', line=dict(color='#1f77b4')))
    fig.add_trace(go.Scatter(x=x_left, y=y_left, fill='toself', mode='lines', name='Ala Sinistra', line=dict(color='#1f77b4')))
    
    fig.update_layout(
        title="Pianta dell'Ala (Vista dall'alto)",
        xaxis_title="Apertura [m]",
        yaxis_title="Corda [m]",
        yaxis_scaleanchor="x", # Mantiene le proporzioni 1:1
        margin=dict(l=0, r=0, t=30, b=0),
        height=350,
        showlegend=False
    )
    return fig

# --- INIZIALIZZAZIONE SESSION STATE ---
if 'results' not in st.session_state:
    st.session_state.results = None

# --- TITOLO ---
st.title("✈️ RCSizer - Preliminary Sizing Tool")
st.markdown("Configura i parametri nella barra laterale e clicca **Esegui** per ottimizzare l'aereo.")

# ==========================================
# SIDEBAR: MENU DI CONFIGURAZIONE
# ==========================================
with st.sidebar:
    st.header("⚙️ Configurazione")
    
    with st.expander("1. Missione", expanded=True):
        V_cruise = st.number_input("Velocità di Crociera (m/s)", value=15.0, step=1.0)
        altitude = st.number_input("Quota Operativa (m)", value=100.0)
        n_limit = st.slider("Fattore di Carico n (G)", min_value=2.0, max_value=10.0, value=4.5)
    
    with st.expander("2. Ala (Target)", expanded=True):
        W_S_target = st.slider("Carico Alare Target (N/m²)", min_value=20.0, max_value=120.0, value=45.0)
        AR_target = st.slider("Allungamento (AR)", min_value=3.0, max_value=10.0, value=6.0)
        airfoil = st.text_input("Profilo Alare (es. NACA2412)", value="NACA2412")
        
        # Parametri per il grafico
        span_input = st.number_input("Apertura (m)", value=1.0, step=0.1)
        chord_root = st.number_input("Corda Radice (m)", value=0.25, step=0.01)
        chord_tip = st.number_input("Corda Punta (m)", value=0.18, step=0.01)
        sweep_le = st.number_input("Sweep LE (°)", value=0.0, step=1.0)
        
    with st.expander("3. Struttura e Stampa"):
        w_e = st.number_input("Larghezza Estrusione w_e (mm)", value=0.45, step=0.05) / 1000.0
        carbon_outer = st.number_input("Tubo Carbonio Diam. Esterno (mm)", value=10.0, step=1.0) / 1000.0
        carbon_inner = st.number_input("Tubo Carbonio Diam. Interno (mm)", value=8.0, step=1.0) / 1000.0
        
    with st.expander("4. Pesi e Bilanciamento"):
        m_motor = st.number_input("Massa Motore (g)", value=150.0) / 1000.0
        x_motor = st.number_input("Posizione Motore (mm)", value=50.0) / 1000.0
        m_batt = st.number_input("Massa Batteria (g)", value=180.0) / 1000.0
        x_batt = st.number_input("Posizione Batteria (mm)", value=350.0) / 1000.0
        
    with st.expander("5. Propulsione"):
        P_max = st.number_input("Potenza Max Motore (W)", value=500.0, step=50.0)
        batt_capacity = st.number_input("Capacità Batteria (Ah)", value=2.2, step=0.1)
        batt_voltage = st.number_input("Voltaggio Batteria (V)", value=11.1, step=0.1)

    st.divider()
    run_btn = st.button("🚀 Esegui Dimensionamento", use_container_width=True, type="primary")


# ==========================================
# AREA PRINCIPALE: VISUALIZZAZIONE LIVE E OUTPUT
# ==========================================

# Mostriamo il grafico della pianta dell'ala in tempo reale
st.subheader("Anteprima Geometria")
fig = plot_wing_planform(span_input, chord_root, chord_tip, sweep_le)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# Esecuzione del motore alla pressione del bottone
if run_btn:
    # Costruzione dell'input JSON
    input_data = {
        "aircraft_type": "trainer",
        "mission": {"V_cruise": V_cruise, "altitude_ops": altitude, "takeoff_mode": "hand_launch", "n_limit_target": n_limit},
        "wing": {
            "panels": [{"span": span_input/2.0, "chord_root": chord_root, "chord_tip": chord_tip, "sweep_LE": math.radians(sweep_le), "airfoil_root": airfoil, "airfoil_tip": airfoil}],
            "W_S_target": W_S_target, "AR_target": AR_target,
            "internal_structure": {"carbon_tube_outer_d": carbon_outer, "carbon_tube_inner_d": carbon_inner, "truss_angle": 0.7854}
        },
        "tail": {"tail_config": "conventional", "S_h": 0.0774, "l_h": 0.6477, "AR_h": 4.0, "S_v": 0.0258, "l_v": 0.6477, "AR_v": 2.0},
        "fuselage": {"L_f": 0.876, "sections": [{"x": 0.0, "width": 0.1, "height": 0.12}, {"x": 0.876, "width": 0.05, "height": 0.06}], "wing_position": 0.25, "tail_position": 0.8},
        "material": "pla",
        "print_process": {"nozzle": 0.0004, "w_e": w_e, "layer_h": 0.0002, "build_volume": [0.22, 0.22, 0.25]},
        "propulsion": {
            "motor": {"P_max": P_max, "mass": m_motor, "x_pos": x_motor},
            "battery": {"cells_S": 3, "cells_P": 1, "capacity_Ah": batt_capacity, "voltage_nominal": batt_voltage, "mass": m_batt, "C_rate_max": 30.0, "x_pos": x_batt},
            "ESC_mass": 0.04, "receiver_mass": 0.02
        }
    }

    with st.spinner("Esecuzione della pipeline di calcolo..."):
        try:
            schema = load_design(input_data)
            registry = ModuleRegistry()
            registry.discover()
            pipeline = Pipeline.from_file(registry, Path("rcsizer/config/pipeline.yaml"))
            st.session_state.results = pipeline.run(schema)
        except Exception as e:
            st.error(f"Errore durante il calcolo: {e}")

# Se abbiamo i risultati, mostriamo le schede
if st.session_state.results:
    d = st.session_state.results.derived
    geo, w, aero, stab, struct, cons, perf = d["geometry"], d["weights"], d["aero"], d["stability"], d["structure"], d["constraints"], d.get("performance", {})

    # Creazione delle Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Overview", "🔬 Dettaglio Ingegneristico", "📐 Parametri CAD"])

    # --- TAB 1: OVERVIEW ---
    with tab1:
        st.subheader("Verdetto del Progetto")
        if cons["is_valid"]:
            st.success("✅ **PROGETTO VALIDO!** L'aereo è bilanciato e sicuro.")
        else:
            st.error("❌ **PROGETTO NON VALIDO!** Ci sono problemi critici.")
        
        for v in cons["violations"]: st.warning(f"⚠️ {v}")
        for a in cons["advices"]: st.info(f"👉 {a}")

        st.divider()
        st.subheader("Metriche Principali")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Peso Totale", f"{w['m_tot']*1000:.1f} g")
        col2.metric("Area Alare", f"{geo['S']:.3f} m²")
        col3.metric("Vel. Stallo", f"{aero['Vs']*3.6:.1f} km/h")
        col4.metric("Autonomia", f"{perf.get('endurance_h', 0)*60:.0f} min")

        st.subheader("Bilanciamento (CG)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Neutral Point", f"{stab['h_n']*100:.1f} % MAC")
        c2.metric("CG Target", f"{stab['h_cg_target']*100:.1f} % MAC")
        c3.metric("CG Attuale", f"{w['h_cg']*100:.1f} % MAC", delta=f"{(w['h_cg'] - stab['h_cg_target'])*100:.1f}% vs Target", delta_color="normal")
        
        if w.get("x_batt_suggested", 0) > 0:
            st.warning(f"💡 **Bilanciamento:** Sposta la batteria a **{w['x_batt_suggested']*1000:.0f} mm** dal muso (ora è a {x_batt*1000:.0f} mm).")

    # --- TAB 2: DETTAGLIO ---
    with tab2:
        st.subheader("Dati Aerodinamici")
        df_aero = pd.DataFrame([
            {"Parametro": "CL_alpha (1/rad)", "Valore": round(aero['CL_alpha'], 3)},
            {"Parametro": "CL_max (3D)", "Valore": round(aero['CLmax'], 3)},
            {"Parametro": "CD0", "Valore": round(aero['CD0'], 4)},
            {"Parametro": "L/D Max", "Valore": round(aero['L_D_max'], 1)},
            {"Parametro": "Re (Crociera)", "Valore": f"{aero['Re']:.0f}"},
            {"Parametro": "Potenza Richiesta (W)", "Valore": round(perf.get('P_req', 0), 1)},
        ])
        st.dataframe(df_aero, use_container_width=True, hide_index=True)

        st.subheader("Verifiche Strutturali")
        df_struct = pd.DataFrame([
            {"Verifica": "Resistenza (MS)", "Valore": round(struct['MS_strength'], 2), "Esito": "OK" if struct['MS_strength'] > 0 else "FALLITO"},
            {"Verifica": "Buckling (MS)", "Valore": round(struct['MS_buckling'], 2), "Esito": "OK" if struct['MS_buckling'] > 0 else "FALLITO"},
            {"Verifica": "Delaminazione (MS)", "Valore": round(struct['MS_delam'], 2), "Esito": "OK" if struct['MS_delam'] > 0 else "FALLITO"},
            {"Verifica": "Spaziatura Centine (mm)", "Valore": round(struct['rib_spacing_max_mm'], 1), "Esito": "OK"},
        ])
        st.dataframe(df_struct, use_container_width=True, hide_index=True)

    # --- TAB 3: CAD ---
    with tab3:
        st.subheader("Quote per il CAD (SolidWorks / Fusion 360)")
        st.info("Usa questi parametri per disegnare l'aereo. Le misure sono in millimetri e gradi.")
        
        cad = d["export"]["cad_parameters"]
        df_cad = pd.DataFrame([
            {"Sezione": "Ala", "Parametro": "Apertura (b)", "Valore": f"{cad['Ala']['Apertura_b_mm']} mm"},
            {"Sezione": "Ala", "Parametro": "Corda Radice", "Valore": f"{cad['Ala']['Corda_Radice_mm']} mm"},
            {"Sezione": "Ala", "Parametro": "Corda Punta", "Valore": f"{cad['Ala']['Corda_Punta_mm']} mm"},
            {"Sezione": "Ala", "Parametro": "MAC", "Valore": f"{cad['Ala']['MAC_mm']} mm"},
            {"Sezione": "Ala", "Parametro": "Diedro Consigliato", "Valore": f"{cad['Ala']['Diedro_Consigliato_gradi']}°"},
            {"Sezione": "Ala", "Parametro": "Svergolamento (Washout)", "Valore": f"{cad['Ala']['Svergolamento_Consigliato_gradi']}°"},
            {"Sezione": "Ala", "Parametro": "Spaziatura Centine", "Valore": f"{cad['Ala']['Spaziatura_Max_Centine_mm']} mm"},
            {"Sezione": "Bilanciamento", "Parametro": "CG Target dal LE", "Valore": f"{cad['Bilanciamento']['CG_Target_mm_dal_LE']} mm"},
        ])
        st.dataframe(df_cad, use_container_width=True, hide_index=True)
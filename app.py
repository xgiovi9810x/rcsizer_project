import streamlit as st
import math
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

from rcsizer.core.loader import load_design
from rcsizer.core.pipeline import Pipeline
from rcsizer.core.registry import ModuleRegistry

st.set_page_config(page_title="RCSizer Wizard", page_icon="✈️", layout="wide")

MISSION_PRESETS = {
    "Trainer (Principiante)": {"V_cruise": 15.0, "n_limit": 4.5, "span": 1.2, "c_r": 0.22, "taper": 0.85, "airfoil": "NACA2412", "S_h": 0.06, "S_v": 0.02, "L_f": 0.9},
    "Acrobatico (3D)": {"V_cruise": 22.0, "n_limit": 8.0, "span": 1.0, "c_r": 0.25, "taper": 0.60, "airfoil": "NACA0012", "S_h": 0.09, "S_v": 0.04, "L_f": 1.0},
    "Aliante (Veleggiatore)": {"V_cruise": 10.0, "n_limit": 5.0, "span": 2.5, "c_r": 0.18, "taper": 0.60, "airfoil": "NACA2412", "S_h": 0.05, "S_v": 0.015, "L_f": 1.1}
}

def plot_planform(c_r, c_t, b, sweep_deg, L_f):
    fig = go.Figure()
    semi = b / 2
    sweep_rad = math.radians(sweep_deg)
    
    x_r = [0, semi, semi, 0, 0]
    y_r = [0, semi * math.tan(sweep_rad), semi * math.tan(sweep_rad) + c_t, c_r, 0]
    x_l = [-x for x in x_r]
    
    fig.add_trace(go.Scatter(x=x_r, y=y_r, fill='toself', name='Ala Dx', line=dict(color='#00E5FF')))
    fig.add_trace(go.Scatter(x=x_l, y=y_r, fill='toself', name='Ala Sx', line=dict(color='#00E5FF')))
    fig.add_trace(go.Scatter(x=[0, 0], y=[-0.1, L_f], mode='lines', name='Fusoliera', line=dict(color='#ff7f0e', width=4)))
    
    limit_x = max(b, L_f) * 0.6 
    fig.update_layout(
        title="Anteprima Geometria (Top View)",
        xaxis_title="Apertura [m]", yaxis_title="Corda/Lunghezza [m]",
        yaxis_scaleanchor="x", 
        xaxis_range=[-limit_x, limit_x], 
        yaxis_range=[-0.2, max(L_f, c_r) + 0.1],
        height=400, margin=dict(l=0, r=0, t=30, b=0),
        showlegend=False, paper_bgcolor="#0E1117", plot_bgcolor="#0E1117", font=dict(color="white")
    )
    return fig

if 'results' not in st.session_state: st.session_state.results = None
if 'saved_designs' not in st.session_state: st.session_state.saved_designs = []

st.title("✈️ RCSizer - Guided Wizard")

with st.sidebar:
    st.header("1. Missione")
    mission_type = st.selectbox("Tipo di Aereo", list(MISSION_PRESETS.keys()), help="Cambia i valori di default.")
    preset = MISSION_PRESETS[mission_type]
    
    st.header("2. Componenti e Pesi")
    m_motor = st.number_input("Peso Motore (g)", value=150)
    m_batt = st.number_input("Peso Batteria (g)", value=200)
    m_electronics = st.number_input("Peso Elettronica (g)", value=80)
    
    st.header("3. Geometria Fisica (Ala)")
    span = st.number_input("Apertura Alare Totale (m)", value=preset["span"], step=0.05, help="La larghezza da punta a punta.")
    c_r = st.number_input("Corda alla Radice (m)", value=preset["c_r"], step=0.01, help="La lunghezza dell'ala vicino alla fusoliera.")
    taper = st.slider("Rastremazione (Tip/Root)", 0.4, 1.0, preset["taper"], help="Rapporto tra corda di punta e di radice.")
    airfoil = st.text_input("Profilo Alare", value=preset["airfoil"])
    sweep = st.slider("Freccia LE (°)", 0.0, 20.0, 0.0)
    
    st.header("4. Fusoliera e Coda")
    L_f = st.number_input("Lunghezza Fusoliera (m)", value=preset["L_f"])
    S_h = st.number_input("Area Coda Orizzontale (m²)", value=preset["S_h"])
    S_v = st.number_input("Area Coda Verticale (m²)", value=preset["S_v"])
    
    st.header("5. Propulsione e Stampa")
    P_max = st.number_input("Potenza Max Motore (W)", value=400)
    batt_capacity = st.number_input("Batteria (Ah)", value=2.2)
    w_e = st.number_input("Spessore Parete (mm)", value=0.45, step=0.05) / 1000.0

    st.divider()
    run_btn = st.button("🚀 Progetta Aereo", use_container_width=True, type="primary")

if st.session_state.results:
    d = st.session_state.results.derived
    b_plot = d["geometry"]["b"] if not math.isnan(d["geometry"]["b"]) else 1.0
    c_r_plot = d["geometry"]["c_r"]
    c_t_plot = d["geometry"]["c_t"]
else:
    b_plot = span
    c_r_plot = c_r
    c_t_plot = c_r * taper

st.plotly_chart(plot_planform(c_r_plot, c_t_plot, b_plot, sweep, L_f), use_container_width=True)

if run_btn:
    input_data = {
        "aircraft_type": "trainer",
        "mission": {"V_cruise": preset["V_cruise"], "altitude_ops": 100.0, "takeoff_mode": "hand_launch", "n_limit_target": preset["n_limit"]},
        "wing": {
            # Passiamo esattamente i valori fisici inseriti
            "panels": [{"span": span/2.0, "chord_root": c_r, "chord_tip": c_r*taper, "sweep_LE": math.radians(sweep), "airfoil_root": airfoil, "airfoil_tip": airfoil}],
            "W_S_target": 60.0, # Fittizio, non verrà usato per ridimensionare
            "AR_target": 6.0,   # Fittizio
            "internal_structure": {"carbon_tube_outer_d": 0.010, "carbon_tube_inner_d": 0.008, "truss_angle": 0.7854}
        },
        "tail": {"tail_config": "conventional", "S_h": S_h, "l_h": L_f*0.7, "AR_h": 4.0, "S_v": S_v, "l_v": L_f*0.7, "AR_v": 2.0},
        "fuselage": {"L_f": L_f, "sections": [{"x": 0.0, "width": 0.1, "height": 0.12}, {"x": L_f, "width": 0.05, "height": 0.06}], "wing_position": 0.25, "tail_position": 0.9},
        "material": "pla",
        "print_process": {"nozzle": 0.0004, "w_e": w_e, "layer_h": 0.0002, "build_volume": [0.22, 0.22, 0.25]},
        "propulsion": {
            "motor": {"P_max": P_max, "mass": m_motor/1000.0, "x_pos": 0.05},
            "battery": {"cells_S": 3, "cells_P": 1, "capacity_Ah": batt_capacity, "voltage_nominal": 11.1, "mass": m_batt/1000.0, "C_rate_max": 30.0, "x_pos": 0.3},
            "ESC_mass": m_electronics/2000.0, "receiver_mass": m_electronics/2000.0
        }
    }

    with st.spinner("Ottimizzazione..."):
        try:
            schema = load_design(input_data)
            registry = ModuleRegistry(); registry.discover()
            pipeline = Pipeline.from_file(registry, Path("rcsizer/config/pipeline.yaml"))
            st.session_state.results = pipeline.run(schema)
        except Exception as e:
            st.error(f"Errore: {e}")

if st.session_state.results:
    d = st.session_state.results.derived
    if math.isnan(d["weights"]["m_tot"]) or math.isinf(d["geometry"]["S"]):
        st.error("⚠️ Configurazione impossibile.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["📊 Overview", "📐 Dati per Costruzione", "⚖️ Confronto Design"])
    
    with tab1:
        cons = d["constraints"]
        if cons["is_valid"]: st.success("✅ Progetto Valido")
        else: st.error("❌ Progetto non valido")
        for a in cons["advices"]: st.info(a)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Peso Totale", f"{d['weights']['m_tot']*1000:.1f} g")
        c2.metric("Area Alare", f"{d['geometry']['S']:.3f} m²")
        c3.metric("AR (risultante)", f"{d['geometry']['AR']:.1f}")
        c4.metric("Carico Alare", f"{(d['weights']['m_tot']*1000)/(d['geometry']['S']*100):.1f} g/dm²")
        
        if st.button("💾 Salva questo design per il confronto"):
            st.session_state.saved_designs.append({
                "Nome": f"Test {len(st.session_state.saved_designs)+1}",
                "Profilo": airfoil,
                "Span (mm)": round(d['geometry']['b']*1000, 1),
                "AR": round(d['geometry']['AR'], 1),
                "Peso (g)": round(d['weights']['m_tot']*1000, 1),
                "Vel. Stallo (km/h)": round(d['aero']['Vs']*3.6, 1),
            })
            st.success("Design salvato!")
        
    with tab2:
        cad = d["export"]["cad_parameters"]
        for section, data in cad.items():
            st.subheader(section)
            st.table(pd.DataFrame(list(data.items()), columns=["Parametro", "Valore"]))
            
    with tab3:
        st.subheader("Confronto Configurazioni")
        if len(st.session_state.saved_designs) == 0:
            st.info("Nessun design salvato.")
        else:
            df = pd.DataFrame(st.session_state.saved_designs)
            st.dataframe(df, use_container_width=True, hide_index=True)
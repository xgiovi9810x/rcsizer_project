"""Entry point CLI con report leggibile."""
from __future__ import annotations
import json
import sys
from pathlib import Path

from rcsizer.core.loader import load_design_from_file
from rcsizer.core.pipeline import Pipeline
from rcsizer.core.registry import ModuleRegistry

CONFIG = Path(__file__).parent / "config" / "pipeline.yaml"

def print_beautiful_report(state) -> None:
    d = state.derived
    geo = d.get("geometry", {})
    w = d.get("weights", {})
    stab = d.get("stability", {})
    aero = d.get("aero", {})
    struct = d.get("structure", {})
    cons = d.get("constraints", {})
    lat = d.get("lateral", {})
    
    line = "=" * 65
    print(f"\n{line}")
    print("  RCSIZER - REPORT DI DIMENSIONAMENTO PRELIMINARE")
    print(f"{line}\n")

    print(" [1] GEOMETRIA E PESI")
    print(f"     Area Alare:      {geo.get('S', 0):.3f} m²")
    print(f"     Apertura:        {geo.get('b', 0):.3f} m")
    print(f"     MAC:             {geo.get('MAC', 0):.3f} m")
    print(f"     Peso Totale:     {w.get('m_tot', 0) * 1000:.1f} g")
    print(f"     Carico Alare:    {(w.get('m_tot', 0) * 1000) / (geo.get('S', 1) * 100):.1f} g/dm²")

    print("\n [2] AERODINAMICA E STABILITA'")
    print(f"     Neutral Point:   {stab.get('h_n', 0) * 100:.1f} % MAC")
    print(f"     CG Target:       {stab.get('h_cg_target', 0) * 100:.1f} % MAC  ({stab.get('h_cg_target', 0) * geo.get('MAC', 0) * 1000:.1f} mm dal LE)")
    print(f"     CG Attuale:      {w.get('h_cg', 0) * 100:.1f} % MAC")
    print(f"     Margine Statico: {stab.get('SM', 0) * 100:.1f} %")
    
    # --- AGGIUNTO: IL CONSIGLIO SULLA BATTERIA ---
    x_batt_sugg = w.get('x_batt_suggested', 0)
    if x_batt_sugg > 0:
        print(f"\n     >> CONSIGLIO BILANCIAMENTO:")
        print(f"        Sposta la batteria a {x_batt_sugg * 1000:.0f} mm dal muso")
        print(f"        (Attuale: {state.input.propulsion.battery.x_pos * 1000:.0f} mm)")
    
    print("\n [3] CONSIGLI STABILITA' LATERALE")
    print(f"     Diedro Consigliato:       {lat.get('dihedral_recommended_deg', 0):.1f}°")
    print(f"     Svergolamento (Washout):  {lat.get('twist_recommended_deg', 0):.1f}°")

    print("\n [4] STRUTTURA (VASE MODE)")
    print(f"     Spaziatura Max Centine:   {struct.get('rib_spacing_max_mm', 0):.1f} mm")
    print(f"     Peso Guscio/Reticolo:     {struct.get('m_wing', 0) * 1000:.1f} g")
    print(f"     Peso Tubo Carbonio:       {struct.get('m_carb_tube', 0.0) * 1000:.1f} g")
    print(f"     Margine Resistenza:       {struct.get('MS_strength', 0):.2f}")
    print(f"     Margine Buckling:         {struct.get('MS_buckling', 0):.2f}")
    
    print(f"\n{line}")
    is_valid = cons.get("is_valid", True)
    if is_valid:
        print("  VERDETTO: PROGETTO VALIDO! ✅")
    else:
        print("  VERDETTO: PROGETTO NON VALIDO! ❌")
        
    for v in cons.get("violations", []):
        print(f"     ! {v}")
    for a in cons.get("advices", []):
        print(f"     > {a}")
    print(f"{line}\n")

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Uso: python -m rcsizer <input.json> [pipeline.yaml]", file=sys.stderr)
        return 2
    input_path = Path(argv[0])
    pipeline_path = Path(argv[1]) if len(argv) > 1 else CONFIG

    state = load_design_from_file(input_path)
    registry = ModuleRegistry()
    registry.discover()
    pipeline = Pipeline.from_file(registry, pipeline_path)
    
    # Esegue la pipeline
    state = pipeline.run(state)
    
    # 1. Stampa il report bello
    print_beautiful_report(state)
    
    # 2. Salva il JSON completo in un file separato per non intasare il terminale
    output_file = input_path.parent / "output_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(state.to_json())
    print(f"Il report JSON completo è stato salvato in: {output_file}\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

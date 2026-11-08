"""fix_wp0.py — Applica le 2 correzioni emerse dal primo run dei test."""
from pathlib import Path

# --- Fix 1: aggiungi `source` a MaterialInput -----------------------------
schema_path = Path("rcsizer/core/schema.py")
src = schema_path.read_text(encoding="utf-8")
old = """    T_glass: float = Field(gt=0)
    flow_factor: float = Field(default=1.0, gt=0)
    density_foam_factor: float = Field(default=1.0, gt=0)"""
new = """    T_glass: float = Field(gt=0)
    flow_factor: float = Field(default=1.0, gt=0)
    density_foam_factor: float = Field(default=1.0, gt=0)
    source: Optional[str] = None"""
if new in src:
    print("Fix 1 già applicato, salto.")
elif old not in src:
    print("ERRORE Fix 1: pattern MaterialInput non trovato!")
else:
    schema_path.write_text(src.replace(old, new), encoding="utf-8")
    print("Fix 1 applicato: MaterialInput ora accetta `source`.")

# --- Fix 2: aggiungi sweep_LE al test -------------------------------------
test_path = Path("rcsizer/tests/test_schema.py")
src = test_path.read_text(encoding="utf-8")
old = """        span={"value": 500, "unit": "mm"},
        chord_root={"value": 250, "unit": "mm"},
        chord_tip={"value": 180, "unit": "mm"},
        airfoil_root="NACA2412", airfoil_tip="NACA2412","""
new = """        span={"value": 500, "unit": "mm"},
        chord_root={"value": 250, "unit": "mm"},
        chord_tip={"value": 180, "unit": "mm"},
        sweep_LE=0.0,
        airfoil_root="NACA2412", airfoil_tip="NACA2412","""
if new in src:
    print("Fix 2 già applicato, salto.")
elif old not in src:
    print("ERRORE Fix 2: pattern del test non trovato!")
else:
    test_path.write_text(src.replace(old, new), encoding="utf-8")
    print("Fix 2 applicato: aggiunto sweep_LE al test.")

print("\nRilancia i test con:")
print("  .venv/bin/python -m pytest -q        # macOS/Linux")
print("  .venv\\Scripts\\python -m pytest -q   # Windows")
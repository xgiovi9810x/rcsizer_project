import math
import numpy as np
from pathlib import Path
from rcsizer.core.state import DesignState, Provenance, ProvenanceKind

name = "airfoil_dat"
version = "1.0.0"
requires = ["input"]
provides = ["airfoil"]

def _parse_dat(filepath: str):
    """Legge un file .dat e restituisce gli array x, y (normalizzati)."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Profilo non trovato: {filepath}")
        
    x_list, y_list = [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    x = float(parts[0])
                    y = float(parts[1])
                    x_list.append(x)
                    y_list.append(y)
                except ValueError:
                    continue # Salta header o righe vuote
    return np.array(x_list), np.array(y_list)

def _compute_airfoil_properties(x, y):
    """Calcola le proprietà geometriche e aerodinamiche del profilo."""
    # 1. Trova il Bordo d'Attacco (LE) e il Bordo d'Uscita (TE)
    idx_le = np.argmin(x)
    x_le, y_le = x[idx_le], y[idx_le]
    
    # Normalizza x tra 0 e 1
    x_norm = (x - x_le) / (x.max() - x_le)
    
    # 2. Dividi in superficie superiore e inferiore
    # (Assumiamo che il file vada da TE -> LE -> TE come il formato Selig)
    x_up, y_up = x_norm[:idx_le+1], y[:idx_le+1]
    x_lo, y_lo = x_norm[idx_le:], y[idx_le:]
    
    # 3. Interpola su una griglia comune con Cosine Spacing
    theta = np.linspace(0, np.pi, 100)
    x_grid = 0.5 * (1 - np.cos(theta))
    
    # np.interp richiede che gli array x siano in ordine crescente
    y_up_grid = np.interp(x_grid, x_up[::-1], y_up[::-1])
    y_lo_grid = np.interp(x_grid, x_lo, y_lo)
    
    # 4. Calcola Linea di Curvatura, Spessore e Camber
    zc = (y_up_grid + y_lo_grid) / 2.0
    thickness = y_up_grid - y_lo_grid
    t_c = np.max(thickness)
    camber = np.max(zc)
    
    # 5. Teoria del Profilo Sottile
    dzc_dx = np.gradient(zc, x_grid)
    
    # Alpha L0
    integrand = dzc_dx * (np.cos(theta) - 1)
    alpha_L0 = -(1.0 / np.pi) * np.trapezoid(integrand, theta)
    
    # cm0 (momento al quarto di corda) - Approssimazione integrale
    A1 = (2.0 / np.pi) * np.trapezoid(dzc_dx * np.cos(theta), theta)
    A2 = (2.0 / np.pi) * np.trapezoid(dzc_dx * np.cos(2 * theta), theta)
    cm0 = (np.pi / 4.0) * (A2 - A1)
    
    # Stima cl_max_2d basata sulla geometria [E]
    cl_max_2d = 0.9 + 2.0 * camber + 1.5 * t_c
    
    return alpha_L0, cm0, t_c, camber, cl_max_2d

def run(state: DesignState) -> DesignState:
    panel = state.input.wing.panels[0]
    profile_name = panel.airfoil_root
    
     # Troviamo il percorso assoluto: risaliamo di 2 cartelle (siamo in rcsizer/modules/airfoil_dat) 
    # e cerchiamo la cartella data
    base_dir = Path(__file__).resolve().parent.parent.parent
    filepath = base_dir / "data" / "airfoils" / f"{profile_name.lower()}.dat"
    
    if not filepath.exists():
        raise FileNotFoundError(f"Impossibile trovare il file del profilo: {filepath}")
        
    x, y = _parse_dat(str(filepath))
    alpha_L0, cm0, t_c, camber, cl_max_2d = _compute_airfoil_properties(x, y)
    
    new_state = state.with_derived(
        "airfoil",
        profile_name=profile_name,
        alpha_L0=alpha_L0,
        camber=camber,
        thickness=t_c,
        cm0=cm0,
        cl_max_2d=cl_max_2d
    )
    
    new_state = new_state.with_provenance(
        "airfoil.alpha_L0", 
        Provenance(source=f"File .dat ({profile_name})", kind=ProvenanceKind.INPUT)
    )
    
    return new_state
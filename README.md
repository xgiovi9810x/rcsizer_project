# RCSizer - Preliminary Sizing Tool for 3D-Printed RC Planes

RCSizer is a modular, Python-based engineering tool designed for the preliminary sizing and optimization of 3D-printed RC aircraft (specifically tailored for vase-mode manufacturing). 

Instead of just verifying a static design, RCSizer acts as an iterative solver: it takes your mission constraints and component weights, and automatically optimizes wing geometry, structural integrity, and center of gravity (CG) placement to converge on a flyable, balanced aircraft.

## Features

The tool is built on a self-discovering plugin architecture, allowing engineers to swap out physics models without touching the core pipeline. The current implementation includes:

### Aerodynamics & Sizing
*   **Airfoil Integration:** Parses standard Selig/UIUC `.dat` files to compute zero-lift angle, moment coefficient, and max lift (using Thin Airfoil Theory).
*   **3D Lift & Drag:** Calculates finite-wing lift-curve slope (DATCOM/Helmbold), form factors (Raymer), skin friction, and induced drag.
*   **Iterative Geometry Sizing:** Automatically scales the wing area and span to meet a target wing loading (`W_S_target`) and aspect ratio (`AR_target`).

### Stability & Trim
*   **Neutral Point Calculation:** Determines the aerodynamic center of the whole aircraft (wing + horizontal tail).
*   **Static Margin & CG Target:** Calculates the safe CG envelope and provides the exact target for the Center of Gravity.
*   **Automated Balancing Act:** Calculates the exact required position for the battery (and other movable components) to achieve the target CG, warning the user if physical constraints (like fuselage length) are exceeded.
*   **Lateral Stability:** Estimates dihedral effect (`Cl_beta`) and provides recommendations for dihedral angle and washout (twist).

### Structural Analysis (Vase Mode)
*   **Truss/Rib Sizing:** Calculates the maximum allowable spacing for internal ribs to prevent local plate buckling.
*   **Carbon Tube Integration:** Supports optional carbon spar tubes and calculates how much bending moment they absorb compared to the printed plastic shell.
*   **Margin of Safety:** Computes structural margins for strength, buckling, and layer delamination (Z-axis weakness).

### CAD Export
*   Outputs a clean JSON table with all the final geometric parameters (in millimeters and degrees), ready to be fed into parametric CAD software (e.g., SolidWorks, Fusion 360, Onshape) for 3D modeling.

---

## Prerequisites

Before installing, ensure you have:
*   **Python 3.11** or higher installed.
*   **Git** installed on your system.
*   A basic understanding of 3D printing (vase mode, extrusion widths) and RC aircraft terminology.

## Installation

It is highly recommended to use a virtual environment to avoid dependency conflicts.

1. **Clone the repository:**
```bash
git clone https://github.com/YOUR_USERNAME/rcsizer_project.git
cd rcsizer_project
```

2. **Create and activate a virtual environment:**
* **Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```
* **macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. **Install the package (editable mode):**
```bash
pip install -e .
```

## Configuration & Data-Driven Design

RCSizer separates the *physics code* from the *empirical constants*. 
*   **`rcsizer/config/coefficients.yaml`**: All empirical coefficients (form factors, safety factors, material knockdowns, etc.) live here. You can tune these values based on your own 3D printing tests without changing a single line of Python code.
*   **`rcsizer/config/materials/`**: Define your filaments (PLA, PETG, LW-PLA) with their specific densities, moduli, and interlayer strengths.
*   **`rcsizer/config/presets/`**: Default targets and bands for different aircraft types (Trainer, Glider, Sport).
*   **`data/airfoils/`**: Drop your `.dat` airfoil coordinate files here.

## Architecture

RCSizer is built to be extensible. The `rcsizer/core/pipeline.py` engine reads a `pipeline.yaml` file to determine the execution order of the physics modules. Modules communicate exclusively through an immutable `DesignState` object, ensuring that every calculation is traceable via a built-in provenance system.

If you want to add a new aerodynamic solver (e.g., a full Lifting-Line method), you simply create a new module folder, define its `requires` and `provides` interfaces, and plug it into the YAML pipeline.

## Disclaimer

This tool has been generate thorugh AI and is designed to provide **preliminary engineering estimates**. While it uses established analytical methods (DATCOM, Raymer, Thin Airfoil Theory), it may contains errors.
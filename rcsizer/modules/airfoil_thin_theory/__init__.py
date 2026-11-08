import math
import numpy as np
from rcsizer.core.state import DesignState, Provenance, ProvenanceKind

name = "airfoil_thin_theory"
version = "1.0.0"
requires = ["input"]
provides = ["airfoil"]

def _naca4_digits(code: str):
    digits = "".join(filter(str.isdigit, code))
    if len(digits) == 4:
        return int(digits[0]), int(digits[1]), int(digits[2:])
    return 0, 0, 12 

def _camber_line(x, m, p):
    if m == 0: return np.zeros_like(x)
    zc = np.zeros_like(x)
    for i, xi in enumerate(x):
        if xi < p:
            zc[i] = (m / (p**2)) * (2*p*xi - xi**2)
        else:
            zc[i] = (m / ((1-p)**2)) * ((1 - 2*p) + 2*p*xi - xi**2)
    return zc

def run(state: DesignState) -> DesignState:
    panel = state.input.wing.panels[0]
    code = panel.airfoil_root
    
    m, p, t = _naca4_digits(code)
    m = m / 100.0
    p = p / 10.0 if p > 0 else 0.4 
    t = t / 100.0
    
    theta = np.linspace(0, math.pi, 100)
    x = 0.5 * (1 - np.cos(theta)) 
    
    zc = _camber_line(x, m, p)
    dzc_dx = np.gradient(zc, x)
    
    integrand = dzc_dx * (np.cos(theta) - 1)
    alpha_L0 = -(1.0 / math.pi) * np.trapezoid(integrand, theta)
    
    t_c = t 
    cl_max_2d = 0.9 + 2.0 * m + 1.5 * t
    
    new_state = state.with_derived(
        "airfoil",
        profile_name=code,
        alpha_L0=alpha_L0,
        camber=m,
        thickness=t_c,
        cm0=-0.05 * m, 
        cl_max_2d=cl_max_2d
    )
    
    new_state = new_state.with_provenance(
        "airfoil.alpha_L0", Provenance(source="4.3 Thin Airfoil", kind=ProvenanceKind.ANALYTIC)
    )
    
    return new_state
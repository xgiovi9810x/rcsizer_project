import math
from rcsizer.core.state import DesignState, Provenance, ProvenanceKind
from rcsizer.core.presets import load_coefficients

name = "stability_classic"
version = "4.0.0"
requires = ["input", "geometry", "aero"]
provides = ["stability"]

def run(state: DesignState) -> DesignState:
    geo = state.derived["geometry"]
    aero = state.derived["aero"]
    inp = state.input
    
    # 1. Geometria Base dell'Ala
    S = geo["S"]
    MAC = geo["MAC"]
    b = geo["b"]
    CL_alpha_w = aero["CL_alpha"]
    h_ac_w = 0.25 # AC dell'ala al 25% della MAC
    AR_w = geo["AR"]
    
    # 2. Dati della Coda (Usa i valori scalati se presenti, altrimenti l'input)
    tail_scaled = state.derived.get("tail_scaled", {})
    tail_in = inp.tail
    
    S_h = tail_scaled.get("S_h", tail_in.S_h or 0.05)
    l_h = tail_scaled.get("l_h", tail_in.l_h or 0.6)
    AR_h = tail_in.AR_h or 4.0 
    
    # 3. Calcolo Pendenze di Portanza
    # Pendenza Coda (DATCOM semplificato per profilo simmetrico)
    CL_alpha_h = (2 * math.pi * AR_h) / (2 + math.sqrt(4 + (AR_h)**2))
    
    # 4. Stima Downwash e Efficienza
    d_eps_dalpha = (2 * CL_alpha_w) / (math.pi * AR_w) if AR_w > 0 else 0.3
    
    # Carica l'efficienza della coda dal file di configurazione
    coeffs = load_coefficients()
    eta_h = coeffs["coefficients"]["eta_h"]["value"]
    
    # 5. Calcolo Volume di Coda Orizzontale (V_H)
    V_H = (S_h * l_h) / (S * MAC) if (S * MAC) > 0 else 0
    
    # 6. CALCOLO NEUTRAL POINT (NP)
    termine_coda = V_H * eta_h * (CL_alpha_h / CL_alpha_w) * (1 - d_eps_dalpha)
    h_n = h_ac_w + termine_coda
    
    # 7. Margine Statico e Limiti CG
    SM_target = 0.12 
    h_cg_target = h_n - SM_target
    
    # Calcoliamo l'SM attuale basandoci sul CG calcolato dal modulo pesi (se esiste)
    # Se non esiste (prima iterazione), usiamo il target
    h_cg_attuale = state.derived.get("weights", {}).get("h_cg", h_cg_target)
    SM_attuale = h_n - h_cg_attuale
    
    # Limiti di sicurezza
    SM_min = 0.05 
    CG_aft_limit = h_n - SM_min
    CG_fwd_limit = h_n - 0.25 

    new_state = state.with_derived(
        "stability",
        h_n=h_n,
        V_H=V_H,
        SM=SM_attuale,
        SM_target=SM_target,
        h_cg_target=h_cg_target,
        CG_aft_limit=CG_aft_limit,
        CG_fwd_limit=CG_fwd_limit,
        S_h=S_h,
        l_h=l_h,
        AR_h=AR_h
    )
    
    new_state = new_state.with_provenance(
        "stability.h_n", 
        Provenance(source="Formula Excel Balance Point", kind=ProvenanceKind.ANALYTIC)
    )
    
    return new_state
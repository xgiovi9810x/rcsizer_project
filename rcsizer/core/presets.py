"""Caricamento preset e materiali da config/ (nessun if tipo == ... nel codice)."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
PRESETS_DIR = CONFIG_DIR / "presets"
MATERIALS_DIR = CONFIG_DIR / "materials"
COEFFS_FILE = CONFIG_DIR / "coefficients.yaml"


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File non trovato: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_preset(aircraft_type: str) -> dict[str, Any]:
    return _read_yaml(PRESETS_DIR / f"{aircraft_type}.yaml")


def load_material(name: str) -> dict[str, Any]:
    return _read_yaml(MATERIALS_DIR / f"{name}.yaml")


def load_coefficients() -> dict[str, Any]:
    return _read_yaml(COEFFS_FILE)


def deep_merge(user: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for k, v in user.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(v, result[k])
        else:
            result[k] = v
    return result

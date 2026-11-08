"""Loader input utente -> InputSchema, con eventuale merge del preset."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .schema import InputSchema
from .presets import load_preset, deep_merge, load_material
from .state import DesignState, new_state


def _resolve_material_ref(raw: dict[str, Any]) -> dict[str, Any]:
    m = raw.get("material")
    if isinstance(m, str):
        raw = dict(raw)
        raw["material"] = load_material(m)
    elif isinstance(m, dict) and "$ref" in m:
        raw = dict(raw)
        raw["material"] = load_material(m["$ref"])
    return raw


def load_input(data: dict[str, Any], apply_preset: bool = True) -> InputSchema:
    data = _resolve_material_ref(data)
    if apply_preset:
        atype = data.get("aircraft_type")
        if atype:
            try:
                preset = load_preset(atype)
                data = deep_merge(data, preset.get("defaults", {}))
            except FileNotFoundError:
                pass
    return InputSchema.model_validate(data)


def load_design(data: dict[str, Any], apply_preset: bool = True) -> DesignState:
    return new_state(load_input(data, apply_preset=apply_preset))


def load_design_from_file(path: str | Path, apply_preset: bool = True) -> DesignState:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return load_design(data, apply_preset=apply_preset)

"""Conversione unità: input utente (mm, g, deg, km/h) -> SI interno (m, kg, rad, m/s)."""
from __future__ import annotations
import math
from typing import Annotated, Any
from pydantic import BeforeValidator, WithJsonSchema

_LENGTH_TO_M = {"m": 1.0, "mm": 1e-3, "cm": 1e-2, "in": 0.0254, "ft": 0.3048}
_MASS_TO_KG = {"kg": 1.0, "g": 1e-3, "lb": 0.45359237}
_ANGLE_TO_RAD = {"rad": 1.0, "deg": math.pi / 180.0}
_SPEED_TO_MS = {"m/s": 1.0, "km/h": 1.0 / 3.6, "kt": 0.514444}
_TIME_TO_S = {"s": 1.0, "min": 60.0, "h": 3600.0}

_TABLES: dict[str, dict[str, float]] = {
    "length": _LENGTH_TO_M,
    "mass": _MASS_TO_KG,
    "angle": _ANGLE_TO_RAD,
    "speed": _SPEED_TO_MS,
    "time": _TIME_TO_S,
}


def convert(value: float, unit: str, dimension: str) -> float:
    table = _TABLES[dimension]
    if unit not in table:
        raise ValueError(
            f"Unità '{unit}' non valida per dimensione '{dimension}'. "
            f"Ammesse: {sorted(table)}"
        )
    return float(value) * table[unit]


def parse_quantity(v: Any, dimension: str) -> float:
    if isinstance(v, dict) and "value" in v and "unit" in v:
        return convert(v["value"], v["unit"], dimension)
    return float(v)


def _mk(dimension: str, name: str, example_unit: str):
    def _conv(v):
        return parse_quantity(v, dimension)

    js = {
        "anyOf": [
            {"type": "number", "description": f"Valore SI ({name})"},
            {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string", "description": f"es. {example_unit}"},
                },
                "required": ["value", "unit"],
            },
        ]
    }
    return Annotated[float, BeforeValidator(_conv), WithJsonSchema(js)]


Length = _mk("length", "m", "mm")
Mass = _mk("mass", "kg", "g")
Angle = _mk("angle", "rad", "deg")
Speed = _mk("speed", "m/s", "km/h")
Time = _mk("time", "s", "min")

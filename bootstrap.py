#!/usr/bin/env python3
"""
bootstrap.py — Crea l'intera struttura di rcsizer WP0 + setup venv + test.

Uso:
    python bootstrap.py

Idempotente: se i file esistono già li sovrascrive (con avviso).
Se .venv/ esiste già, lo salta.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


# ============================================================================
# CONTENUTO DEI FILE
# La stringa di ogni file è in r'''...''' (raw string). Per i file che
# contengono ''' al loro interno (test_registry.py, test_pipeline.py) uso
# il placeholder @TS@ che viene sostituito dopo.
# ============================================================================

FILES: dict[str, str] = {}


FILES["pyproject.toml"] = r'''
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "rcsizer"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.5",
    "pyyaml>=6.0",
    "pytest>=7.4",
]

[tool.pytest.ini_options]
testpaths = ["rcsizer/tests"]
'''.lstrip()


FILES["README.md"] = r'''
# rcsizer — WP0

Core per il tool di dimensionamento RC (specifica v2). Include:
1. `DesignState` immutabile, serializzabile, con provenance per valore derivato.
2. Schema di input (sez. 3) in Pydantic v2: SI interni, `{value, unit}` accettati.
3. Conversione mm/g/deg -> SI al bordo di I/O (units.py).
4. Preset per tipo da `config/presets/`, materiali da `config/materials/`.
5. Registro moduli auto-scansionato (`modules/`) con interfaccia name/version/requires/provides/run.
6. Motore pipeline da `pipeline.yaml` con topo-sort e fallback su cicli.
7. Coefficienti empirici [E] isolati in `coefficients.yaml`.
8. Test di accettazione: rifiuto input errato, round-trip JSON, modulo finto con una sola cartella.
9. `schema.json` generabile via `scripts/generate_schema.py`.
10. CLI minima: `python -m rcsizer input.json [pipeline.yaml]`.
'''.lstrip()


FILES["scripts/generate_schema.py"] = r'''
"""Esporta lo JSON Schema dello schema di input in schema.json."""
import json
from pathlib import Path
from rcsizer.core.schema import InputSchema

if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "schema.json"
    out.write_text(
        json.dumps(InputSchema.model_json_schema(), indent=2),
        encoding="utf-8",
    )
    print(f"Scritto {out}")
'''.lstrip()


# --- Package rcsizer -------------------------------------------------------
FILES["rcsizer/__init__.py"] = r'''
"""rcsizer — RC Plane Sizing Tool (core)."""
__version__ = "0.1.0"
'''.lstrip()


FILES["rcsizer/__main__.py"] = r'''
"""Entry point CLI minimale: python -m rcsizer input.json"""
from __future__ import annotations
import json
import sys
from pathlib import Path

from rcsizer.core.loader import load_design_from_file
from rcsizer.core.pipeline import Pipeline
from rcsizer.core.registry import ModuleRegistry

CONFIG = Path(__file__).parent / "config" / "pipeline.yaml"


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
    state = pipeline.run(state)
    print(state.to_json())
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''.lstrip()


FILES["rcsizer/core/__init__.py"] = ""


FILES["rcsizer/core/units.py"] = r'''
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
'''.lstrip()


FILES["rcsizer/core/schema.py"] = r'''
"""Schema di input (sez. 3). Unità interne SI; accetta {value, unit} sui campi
tipizzati come Length/Mass/Angle/Speed/Time (definiti in units.py)."""
from __future__ import annotations
from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .units import Length, Mass, Angle, Speed, Time


class AircraftType(str, Enum):
    TRAINER = "trainer"
    SPORT = "sport"
    AEROBATIC = "aerobatic"
    THREE_D = "3d"
    GLIDER = "glider"
    MOTORGLIDER = "motorglider"
    FLYING_WING = "flying_wing"
    DELTA = "delta"
    WARBIRD_SCALE = "warbird_scale"
    FPV_LONGRANGE = "fpv_longrange"
    CANARD = "canard"


class TakeoffMode(str, Enum):
    RUNWAY = "runway"
    HAND_LAUNCH = "hand_launch"
    CATAPULT = "catapult"


class WingPositionZ(str, Enum):
    HIGH = "high"
    MID = "mid"
    LOW = "low"


class TailConfig(str, Enum):
    CONVENTIONAL = "conventional"
    T_TAIL = "T"
    CRUCIFORM = "cruciform"
    V_TAIL = "V"
    H_TAIL = "H"
    CANARD = "canard"
    NONE = "none"


class ControlSurfaceType(str, Enum):
    AILERON = "aileron"
    FLAP = "flap"
    ELEVON = "elevon"
    FLAPERON = "flaperon"


class ComponentSource(str, Enum):
    MANUAL = "manual"
    DERIVED_GEOMETRY = "derived_geometry"
    CAD_EXPORT = "cad_export"


class FuselageShape(str, Enum):
    ELLIPSE = "ellipse"
    ROUNDED_RECT = "rounded_rect"


_FROZEN = ConfigDict(frozen=True, extra="forbid")


class MissionInput(BaseModel):
    model_config = _FROZEN
    V_cruise: Speed = Field(gt=0)
    V_max_target: Optional[Speed] = Field(default=None, gt=0)
    endurance_target: Optional[Time] = Field(default=None, gt=0)
    range_target: Optional[Length] = Field(default=None, gt=0)
    altitude_ops: Length = Field(gt=0)
    takeoff_mode: TakeoffMode
    payload_mass: Mass = Field(default=0.0, ge=0)
    wind_design: Speed = Field(default=0.0, ge=0)
    n_limit_target: float = Field(gt=0)


class PanelInput(BaseModel):
    model_config = _FROZEN
    span: Length = Field(gt=0)
    chord_root: Length = Field(gt=0)
    chord_tip: Length = Field(gt=0)
    sweep_LE: Optional[Angle] = Field(default=None)
    sweep_c4: Optional[Angle] = Field(default=None)
    dihedral: Angle = Field(default=0.0)
    twist_tip: Angle = Field(default=0.0)
    airfoil_root: str
    airfoil_tip: str
    incidence_root: Angle = Field(default=0.0)

    @model_validator(mode="after")
    def _sweep_present(self):
        if self.sweep_LE is None and self.sweep_c4 is None:
            raise ValueError("PanelInput richiede sweep_LE oppure sweep_c4")
        return self


class ControlSurfaceInput(BaseModel):
    model_config = _FROZEN
    type: ControlSurfaceType
    y_inner: float = Field(ge=0, le=1)
    y_outer: float = Field(ge=0, le=1)
    chord_ratio: float = Field(gt=0, lt=1)
    deflection_max: Angle = Field(gt=0)

    @model_validator(mode="after")
    def _y_order(self):
        if self.y_outer <= self.y_inner:
            raise ValueError("y_outer deve essere > y_inner")
        return self


class WingInput(BaseModel):
    model_config = _FROZEN
    panels: list[PanelInput] = Field(min_length=1)
    wing_airfoil: Optional[str] = None
    wing_position_z: WingPositionZ = WingPositionZ.MID
    control_surfaces: list[ControlSurfaceInput] = Field(default_factory=list)
    fillet_wing_fuselage: bool = False
    winglets: bool = False


class TailInput(BaseModel):
    model_config = _FROZEN
    tail_config: TailConfig
    S_h: Optional[float] = Field(default=None, gt=0)
    AR_h: Optional[float] = Field(default=None, gt=0)
    taper_h: Optional[float] = Field(default=None, gt=0)
    profile_h: Optional[str] = None
    incidence_h: Angle = Field(default=0.0)
    elevator_chord_ratio: Optional[float] = Field(default=None, gt=0, lt=1)
    S_v: Optional[float] = Field(default=None, gt=0)
    AR_v: Optional[float] = Field(default=None, gt=0)
    rudder_chord_ratio: Optional[float] = Field(default=None, gt=0, lt=1)
    l_h: Optional[Length] = Field(default=None, gt=0)
    l_v: Optional[Length] = Field(default=None, gt=0)
    S_vtail: Optional[float] = Field(default=None, gt=0)
    dihedral_V: Optional[Angle] = Field(default=None)


class FuselageSection(BaseModel):
    model_config = _FROZEN
    x: Length
    width: Length = Field(gt=0)
    height: Length = Field(gt=0)
    shape: FuselageShape = FuselageShape.ELLIPSE


class FuselageInput(BaseModel):
    model_config = _FROZEN
    L_f: Length = Field(gt=0)
    sections: list[FuselageSection] = Field(min_length=2)
    wing_position: Length
    tail_position: Length


class MaterialInput(BaseModel):
    model_config = _FROZEN
    name: str
    rho_filament: float = Field(gt=0)
    E_xy: float = Field(gt=0)
    E_z: float = Field(gt=0)
    sigma_y_xy: float = Field(gt=0)
    sigma_y_z: float = Field(gt=0)
    G: float = Field(gt=0)
    nu: float = Field(ge=0, lt=0.5)
    T_glass: float = Field(gt=0)
    flow_factor: float = Field(default=1.0, gt=0)
    density_foam_factor: float = Field(default=1.0, gt=0)


class PrintProcessInput(BaseModel):
    model_config = _FROZEN
    nozzle: Length = Field(gt=0)
    w_e: Length = Field(gt=0)
    layer_h: Length = Field(gt=0)
    mode: Literal["vase"] = "vase"
    build_volume: tuple[Length, Length, Length]
    roughness_k: float = Field(default=0.0, ge=0)
    knockdown_layer: float = Field(default=1.0, gt=0, le=1)


class CoatingInput(BaseModel):
    model_config = _FROZEN
    name: str
    mass_per_m2: float = Field(ge=0)


class MotorInput(BaseModel):
    model_config = _FROZEN
    P_max: float = Field(gt=0)
    kV: Optional[float] = Field(default=None, gt=0)
    mass: Mass = Field(gt=0)
    thrust_static: Optional[float] = Field(default=None, ge=0)
    prop_D: Optional[Length] = Field(default=None, gt=0)
    prop_pitch: Optional[Length] = Field(default=None, gt=0)


class BatteryInput(BaseModel):
    model_config = _FROZEN
    cells_S: int = Field(gt=0)
    cells_P: int = Field(gt=0)
    capacity_Ah: float = Field(gt=0)
    voltage_nominal: float = Field(gt=0)
    mass: Mass = Field(gt=0)
    usable_fraction: float = Field(default=0.8, gt=0, le=1)
    C_rate_max: float = Field(gt=0)


class ServoInput(BaseModel):
    model_config = _FROZEN
    count: int = Field(ge=0)
    mass_each: Mass = Field(ge=0)
    torque: Optional[float] = Field(default=None, ge=0)


class PropulsionInput(BaseModel):
    model_config = _FROZEN
    motor: MotorInput
    battery: BatteryInput
    ESC_mass: Mass = Field(default=0.0, ge=0)
    receiver_mass: Mass = Field(default=0.0, ge=0)
    servos: Optional[ServoInput] = None
    wiring_mass: Mass = Field(default=0.0, ge=0)
    landing_gear_mass: Mass = Field(default=0.0, ge=0)


class ComponentInput(BaseModel):
    model_config = _FROZEN
    name: str
    mass: Mass = Field(ge=0)
    x: Length
    y: Length
    z: Length
    x_range: Optional[tuple[Length, Length]] = None
    source: ComponentSource = ComponentSource.MANUAL


class InputSchema(BaseModel):
    model_config = _FROZEN
    aircraft_type: AircraftType
    mission: MissionInput
    wing: WingInput
    tail: TailInput
    fuselage: FuselageInput
    material: MaterialInput
    print_process: PrintProcessInput
    coating: Optional[CoatingInput] = None
    propulsion: PropulsionInput
    components: list[ComponentInput] = Field(default_factory=list)
'''.lstrip()


FILES["rcsizer/core/state.py"] = r'''
"""DesignState: stato immutabile della pipeline, serializzabile in JSON."""
from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from .schema import InputSchema


class ProvenanceKind(str, Enum):
    ANALYTIC = "A"
    EMPIRICAL = "E"
    INPUT = "I"
    DERIVED = "D"
    DEFAULT = "F"


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True)
    source: str
    kind: ProvenanceKind
    iteration: int = 0
    notes: str | None = None


class Warning(BaseModel):
    model_config = ConfigDict(frozen=True)
    code: str
    severity: str = "warning"
    message: str
    field: str | None = None
    iteration: int = 0


_FROZEN = ConfigDict(frozen=True, extra="forbid")


class DesignState(BaseModel):
    model_config = _FROZEN

    input: InputSchema
    derived: dict[str, dict[str, Any]] = Field(default_factory=dict)
    provenance: dict[str, Provenance] = Field(default_factory=dict)
    warnings: tuple[Warning, ...] = ()
    iteration: int = 0

    def with_derived(self, namespace: str, **kwargs: Any) -> "DesignState":
        new_derived = {k: dict(v) for k, v in self.derived.items()}
        new_derived.setdefault(namespace, {}).update(kwargs)
        return self.model_copy(update={"derived": new_derived})

    def with_provenance(self, path: str, prov: Provenance) -> "DesignState":
        new_prov = dict(self.provenance)
        new_prov[path] = prov
        return self.model_copy(update={"provenance": new_prov})

    def with_warning(self, w: Warning) -> "DesignState":
        return self.model_copy(update={"warnings": self.warnings + (w,)})

    def with_iteration(self, it: int) -> "DesignState":
        return self.model_copy(update={"iteration": it})

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, s: str) -> "DesignState":
        return cls.model_validate_json(s)


def new_state(validated: InputSchema) -> DesignState:
    return DesignState(input=validated)
'''.lstrip()


FILES["rcsizer/core/presets.py"] = r'''
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
'''.lstrip()


FILES["rcsizer/core/loader.py"] = r'''
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
'''.lstrip()


FILES["rcsizer/core/registry.py"] = r'''
"""Registro moduli: scansione automatica di rcsizer/modules/."""
from __future__ import annotations
import importlib
import pkgutil
import sys
from dataclasses import dataclass
from typing import Callable

from .state import DesignState


@dataclass(frozen=True)
class ModuleInterface:
    name: str
    version: str
    requires: tuple[str, ...]
    provides: tuple[str, ...]


@dataclass
class RegisteredModule:
    interface: ModuleInterface
    run: Callable[[DesignState], DesignState]


_REQUIRED_ATTRS = ("name", "version", "requires", "provides", "run")


class ModuleRegistry:
    def __init__(self) -> None:
        self.modules: dict[str, RegisteredModule] = {}

    def register(self, module) -> None:
        missing = [a for a in _REQUIRED_ATTRS if not hasattr(module, a)]
        if missing:
            raise ValueError(
                f"Modulo '{getattr(module, '__name__', '?')}' manca attributi: {missing}"
            )
        iface = ModuleInterface(
            name=module.name,
            version=module.version,
            requires=tuple(module.requires),
            provides=tuple(module.provides),
        )
        self.modules[iface.name] = RegisteredModule(iface, module.run)

    def discover(self, package: str = "rcsizer.modules") -> None:
        importlib.import_module(package)
        pkg = sys.modules[package]
        for _, modname, is_pkg in pkgutil.iter_modules(pkg.__path__):
            if not is_pkg:
                continue
            full = f"{package}.{modname}"
            module = importlib.import_module(full)
            if not hasattr(module, "run"):
                continue
            self.register(module)

    def get(self, name: str) -> RegisteredModule:
        if name not in self.modules:
            raise KeyError(
                f"Modulo non registrato: '{name}'. Disponibili: {sorted(self.modules)}"
            )
        return self.modules[name]
'''.lstrip()


FILES["rcsizer/core/pipeline.py"] = r'''
"""Motore di pipeline: legge pipeline.yaml, risolve l'ordine, esegue."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional
import yaml
from pydantic import BaseModel, ConfigDict, Field

from .state import DesignState, Warning
from .registry import ModuleRegistry


class PipelineStage(BaseModel):
    model_config = ConfigDict(extra="allow")
    impl: str


class LoopConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variables: list[str] = Field(default_factory=list)
    tolerance: dict[str, float] = Field(default_factory=dict)
    max_iter: int = 30


class PipelineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pipeline: list[dict[str, PipelineStage]]
    loop: Optional[LoopConfig] = None


class Pipeline:
    def __init__(self, registry: ModuleRegistry, config: PipelineConfig) -> None:
        self.registry = registry
        self.config = config
        self._stages: list[tuple[str, str]] = self._parse_stages()
        self._order: list[str] = self._resolve_order()

    def _parse_stages(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for entry in self.config.pipeline:
            if len(entry) != 1:
                raise ValueError(f"Ogni stage deve avere una sola chiave, trovato: {entry}")
            (stage_name, cfg), = entry.items()
            out.append((stage_name, cfg.impl))
        return out

    def _resolve_order(self) -> list[str]:
        impl_names = [impl for _, impl in self._stages]
        field_to_impl: dict[str, str] = {}
        for impl in impl_names:
            reg = self.registry.get(impl)
            for f in reg.interface.provides:
                field_to_impl[f] = impl

        deps: dict[str, set[str]] = {impl: set() for impl in impl_names}
        for impl in impl_names:
            reg = self.registry.get(impl)
            for f in reg.interface.requires:
                if f in field_to_impl and field_to_impl[f] != impl:
                    deps[impl].add(field_to_impl[f])

        try:
            ordered: list[str] = []
            visited: set[str] = set()
            visiting: set[str] = set()

            def visit(n: str) -> None:
                if n in visited:
                    return
                if n in visiting:
                    raise ValueError(f"Dipendenza ciclica su '{n}'")
                visiting.add(n)
                for d in deps[n]:
                    visit(d)
                visiting.discard(n)
                visited.add(n)
                ordered.append(n)

            for impl in impl_names:
                visit(impl)
            return ordered
        except ValueError:
            return impl_names

    def _validate_requires(self) -> None:
        required: set[str] = set()
        provided: set[str] = {"input"}
        for _, impl in self._stages:
            reg = self.registry.get(impl)
            required.update(reg.interface.requires)
            provided.update(reg.interface.provides)
        missing = required - provided
        if missing:
            raise ValueError(f"Campi richiesti non forniti da alcun modulo: {sorted(missing)}")

    def run_once(self, state: DesignState) -> DesignState:
        self._validate_requires()
        for impl in self._order:
            state = self.registry.get(impl).run(state)
        return state

    def run(self, state: DesignState) -> DesignState:
        if self.config.loop is None:
            return self.run_once(state)
        return self._run_fixed_point(state, self.config.loop)

    def _run_fixed_point(self, state: DesignState, loop: LoopConfig) -> DesignState:
        prev_vals: dict[str, float] = {}
        for it in range(loop.max_iter):
            state = self.run_once(state).with_iteration(it)
            cur_vals: dict[str, float] = {}
            for var in loop.variables:
                v = self._read_var(state, var)
                if isinstance(v, (int, float)):
                    cur_vals[var] = float(v)
            if it > 0 and self._converged(prev_vals, cur_vals, loop.tolerance):
                return state
            prev_vals = cur_vals
        state = state.with_warning(Warning(
            code="pipeline.max_iter",
            severity="warning",
            message=f"Pipeline non convergente in {loop.max_iter} iterazioni",
        ))
        return state

    @staticmethod
    def _read_var(state: DesignState, var: str) -> Any:
        parts = var.split(".")
        if len(parts) == 2:
            ns, key = parts
            return state.derived.get(ns, {}).get(key)
        return None

    @staticmethod
    def _converged(prev: dict[str, float], cur: dict[str, float],
                   tol: dict[str, float]) -> bool:
        for k, v_cur in cur.items():
            if k not in prev:
                return False
            denom = max(abs(prev[k]), 1e-9)
            if abs(v_cur - prev[k]) / denom > tol.get(k, 1e-3):
                return False
        return True

    @classmethod
    def from_file(cls, registry: ModuleRegistry, path: str | Path) -> "Pipeline":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(registry, PipelineConfig.model_validate(data))
'''.lstrip()


FILES["rcsizer/modules/__init__.py"] = '"""Moduli M1–M9 (vuoti in WP0; popolati nei WP1–WP9)."""\n'


# --- Config ----------------------------------------------------------------
FILES["rcsizer/config/pipeline.yaml"] = r'''
pipeline:
  - airfoil:      {impl: airfoil_thin_theory}
  - geometry:     {impl: geometry_trapezoid}
  - aero:         {impl: aero_datcom}
  - stability:    {impl: stability_classic}
  - structure:    {impl: structure_vasem_shell}
  - weights:      {impl: weights_table}
  - performance:  {impl: performance_basic}
  - export:       {impl: export_params_table}
loop:
  variables: [weights.W, weights.h_cg]
  tolerance: {weights.W: 1e-3, weights.h_cg: 5e-4}
  max_iter: 30
'''.lstrip()


FILES["rcsizer/config/coefficients.yaml"] = r'''
# Coefficienti empirici [E] — nessuna costante magica nel codice.
coefficients:
  S_wet_w_factor:
    value: 2.5
    source: "sez. 4.2"
    range: [2.2, 2.8]
    confidence: low
    kind: E
  k_roughness:
    value: 0.20
    source: "sez. 4.4"
    range: [0.10, 0.30]
    confidence: low
    kind: E
  CD_misc_fraction:
    value: 0.10
    source: "sez. 4.4"
    range: [0.05, 0.15]
    confidence: low
    kind: E
  eta_h:
    value: 0.90
    source: "sez. 4.5"
    range: [0.85, 1.0]
    confidence: low
    kind: E
  gamma_buckling:
    value: 0.30
    source: "sez. 4.9"
    range: [0.2, 0.4]
    confidence: low
    kind: E
  tau_elevator:
    value: 0.50
    source: "sez. 4.5"
    range: [0.4, 0.6]
    confidence: low
    kind: E
  launch_n_factor:
    value: 4.0
    source: "sez. 4.9"
    range: [3, 6]
    confidence: low
    kind: E
'''.lstrip()


FILES["rcsizer/config/presets/trainer.yaml"] = r'''
aircraft_type: trainer
targets:
  W_over_S_N_m2: [50, 80]
  CLmax: [1.2, 1.5]
  SM_pct: [10, 15]
  V_H: [0.50, 0.70]
  V_V: [0.035, 0.05]
  n_limit: [4, 5]
defaults:
  mission:
    V_cruise: 15.0
    altitude_ops: 100.0
    takeoff_mode: hand_launch
    n_limit_target: 4.5
    wind_design: 3.0
    payload_mass: 0.0
'''.lstrip()


FILES["rcsizer/config/presets/sport.yaml"] = r'''
aircraft_type: sport
targets:
  W_over_S_N_m2: [70, 110]
  CLmax: [1.1, 1.4]
  SM_pct: [8, 12]
  V_H: [0.45, 0.60]
  V_V: [0.03, 0.045]
  n_limit: [6]
defaults:
  mission:
    V_cruise: 22.0
    altitude_ops: 150.0
    takeoff_mode: runway
    n_limit_target: 6.0
'''.lstrip()


FILES["rcsizer/config/presets/glider.yaml"] = r'''
aircraft_type: glider
targets:
  W_over_S_N_m2: [25, 60]
  CLmax: [1.1, 1.5]
  SM_pct: [5, 12]
  V_H: [0.40, 0.60]
  V_V: [0.025, 0.045]
  n_limit: [-7, 7]
defaults:
  mission:
    V_cruise: 12.0
    altitude_ops: 200.0
    takeoff_mode: hand_launch
    n_limit_target: 7.0
'''.lstrip()


FILES["rcsizer/config/materials/pla.yaml"] = r'''
name: PLA
rho_filament: 1240.0
E_xy: 3.5e9
E_z: 2.5e9
sigma_y_xy: 50e6
sigma_y_z: 25e6
G: 1.3e9
nu: 0.35
T_glass: 328.15
flow_factor: 1.0
density_foam_factor: 1.0
source: "letteratura stampa 3D [E]"
'''.lstrip()


FILES["rcsizer/config/materials/petg.yaml"] = r'''
name: PETG
rho_filament: 1270.0
E_xy: 2.1e9
E_z: 1.9e9
sigma_y_xy: 50e6
sigma_y_z: 30e6
G: 0.8e9
nu: 0.40
T_glass: 353.15
flow_factor: 1.0
density_foam_factor: 1.0
source: "letteratura stampa 3D [E]"
'''.lstrip()


# --- Test ------------------------------------------------------------------
FILES["rcsizer/tests/__init__.py"] = ""


FILES["rcsizer/tests/conftest.py"] = r'''
import pytest
from rcsizer.core.schema import (
    InputSchema, MissionInput, WingInput, PanelInput, TailInput, FuselageInput,
    FuselageSection, MaterialInput, PrintProcessInput, PropulsionInput,
    MotorInput, BatteryInput, AircraftType, TakeoffMode,
)


def _minimal_panel() -> PanelInput:
    return PanelInput(
        span=0.5, chord_root=0.25, chord_tip=0.18,
        sweep_LE=0.0, dihedral=0.0, twist_tip=0.0, incidence_root=0.0,
        airfoil_root="NACA2412", airfoil_tip="NACA2412",
    )


@pytest.fixture
def minimal_input() -> InputSchema:
    return InputSchema(
        aircraft_type=AircraftType.TRAINER,
        mission=MissionInput(
            V_cruise=15.0, altitude_ops=100.0,
            takeoff_mode=TakeoffMode.HAND_LAUNCH, n_limit_target=4.5,
        ),
        wing=WingInput(panels=[_minimal_panel()]),
        tail=TailInput(tail_config="conventional"),
        fuselage=FuselageInput(
            L_f=1.0,
            sections=[
                FuselageSection(x=0.0, width=0.10, height=0.12),
                FuselageSection(x=1.0, width=0.05, height=0.06),
            ],
            wing_position=0.3, tail_position=0.9,
        ),
        material=MaterialInput(
            name="PLA", rho_filament=1240.0,
            E_xy=3.5e9, E_z=2.5e9, sigma_y_xy=50e6, sigma_y_z=25e6,
            G=1.3e9, nu=0.35, T_glass=328.15,
        ),
        print_process=PrintProcessInput(
            nozzle=0.4e-3, w_e=0.45e-3, layer_h=0.2e-3,
            build_volume=(0.22, 0.22, 0.25),
        ),
        propulsion=PropulsionInput(
            motor=MotorInput(P_max=300.0, mass=0.05),
            battery=BatteryInput(
                cells_S=3, cells_P=1, capacity_Ah=1.5,
                voltage_nominal=11.1, mass=0.12, C_rate_max=30.0,
            ),
        ),
    )
'''.lstrip()


FILES["rcsizer/tests/test_units.py"] = r'''
import pytest
from rcsizer.core.units import convert, parse_quantity


def test_mm_to_m():
    assert convert(500.0, "mm", "length") == pytest.approx(0.5)


def test_g_to_kg():
    assert convert(250.0, "g", "mass") == pytest.approx(0.25)


def test_deg_to_rad():
    assert convert(180.0, "deg", "angle") == pytest.approx(3.14159265, rel=1e-6)


def test_parse_quantity_accepts_number_as_SI():
    assert parse_quantity(1.5, "mass") == 1.5


def test_parse_quantity_accepts_annotated_dict():
    assert parse_quantity({"value": 3, "unit": "in"}, "length") == pytest.approx(0.0762)


def test_unknown_unit_raises():
    with pytest.raises(ValueError, match="Unità 'zz' non valida"):
        convert(1.0, "zz", "length")
'''.lstrip()


FILES["rcsizer/tests/test_schema.py"] = r'''
import pytest
from pydantic import ValidationError
from rcsizer.core.schema import (
    InputSchema, PanelInput, WingInput, AircraftType, MissionInput,
    FuselageInput, FuselageSection, MaterialInput, PrintProcessInput,
    PropulsionInput, MotorInput, BatteryInput, TailInput, TakeoffMode,
)


def test_negative_span_rejected():
    with pytest.raises(ValidationError) as exc:
        PanelInput(
            span=-0.5, chord_root=0.2, chord_tip=0.1,
            airfoil_root="NACA2412", airfoil_tip="NACA2412",
        )
    msg = str(exc.value)
    assert "span" in msg
    assert "greater than 0" in msg


def test_unknown_field_rejected():
    with pytest.raises(ValidationError) as exc:
        PanelInput(
            span=0.5, chord_root=0.2, chord_tip=0.1,
            airfoil_root="A", airfoil_tip="A",
            bogus_field=1.0,
        )
    assert "bogus_field" in str(exc.value)


def test_unit_annotated_input_accepted():
    p = PanelInput(
        span={"value": 500, "unit": "mm"},
        chord_root={"value": 250, "unit": "mm"},
        chord_tip={"value": 180, "unit": "mm"},
        airfoil_root="NACA2412", airfoil_tip="NACA2412",
    )
    assert p.span == pytest.approx(0.5)
    assert p.chord_root == pytest.approx(0.25)


def test_missing_required_field_rejected():
    with pytest.raises(ValidationError) as exc:
        PanelInput(
            chord_root=0.2, chord_tip=0.1,
            airfoil_root="A", airfoil_tip="A",
        )
    assert "span" in str(exc.value)
'''.lstrip()


FILES["rcsizer/tests/test_state.py"] = r'''
import pytest
from rcsizer.core.state import new_state, Provenance, ProvenanceKind, Warning


def test_state_is_frozen(minimal_input):
    s = new_state(minimal_input)
    with pytest.raises(Exception):
        s.iteration = 5


def test_with_derived_returns_new_state(minimal_input):
    s0 = new_state(minimal_input)
    s1 = s0.with_derived("aero", CLmax=1.3)
    assert s0.derived == {}
    assert s1.derived["aero"]["CLmax"] == 1.3
    assert s1 is not s0


def test_with_provenance(minimal_input):
    s = new_state(minimal_input).with_provenance(
        "aero.CLmax", Provenance(source="4.4", kind=ProvenanceKind.ANALYTIC)
    )
    assert s.provenance["aero.CLmax"].source == "4.4"


def test_warning_accumulation(minimal_input):
    s = new_state(minimal_input)
    s = s.with_warning(Warning(code="w1", message="m1"))
    s = s.with_warning(Warning(code="w2", message="m2"))
    assert len(s.warnings) == 2
'''.lstrip()


FILES["rcsizer/tests/test_roundtrip.py"] = r'''
"""Test di accettazione: round-trip di serializzazione identico."""
from rcsizer.core.state import DesignState, new_state, Provenance, ProvenanceKind, Warning


def test_input_schema_roundtrip(minimal_input):
    s = minimal_input.model_dump_json()
    again = type(minimal_input).model_validate_json(s)
    assert again == minimal_input


def test_design_state_roundtrip(minimal_input):
    s = (
        new_state(minimal_input)
        .with_derived("aero", CLmax=1.25, CL_alpha=4.8)
        .with_derived("geometry", S=0.35, AR=6.5)
        .with_provenance(
            "aero.CLmax",
            Provenance(source="4.4", kind=ProvenanceKind.ANALYTIC, iteration=1),
        )
        .with_warning(Warning(code="w", message="x", iteration=1))
        .with_iteration(1)
    )
    js = s.to_json()
    back = DesignState.from_json(js)
    assert back.to_json() == js
    assert back == s
'''.lstrip()


FILES["rcsizer/tests/test_presets.py"] = r'''
import pytest
from rcsizer.core.presets import load_preset, load_material, deep_merge
from rcsizer.core.loader import load_input


def test_preset_trainer_loads():
    p = load_preset("trainer")
    assert p["aircraft_type"] == "trainer"
    assert "defaults" in p


def test_material_pla_loads():
    m = load_material("pla")
    assert m["name"] == "PLA"
    assert m["rho_filament"] > 0


def test_deep_merge_user_wins():
    base = {"a": {"x": 1, "y": 2}, "b": 3}
    user = {"a": {"y": 99}, "b": 4}
    merged = deep_merge(user, base)
    assert merged == {"a": {"x": 1, "y": 99}, "b": 4}


def test_load_input_applies_preset_defaults():
    data = {
        "aircraft_type": "trainer",
        "mission": {
            "altitude_ops": 100.0,
            "takeoff_mode": "hand_launch",
            "n_limit_target": 4.5,
        },
        "wing": {"panels": [{
            "span": 0.5, "chord_root": 0.25, "chord_tip": 0.18,
            "sweep_LE": 0.0,
            "airfoil_root": "NACA2412", "airfoil_tip": "NACA2412",
        }]},
        "tail": {"tail_config": "conventional"},
        "fuselage": {
            "L_f": 1.0,
            "sections": [
                {"x": 0.0, "width": 0.1, "height": 0.12},
                {"x": 1.0, "width": 0.05, "height": 0.06},
            ],
            "wing_position": 0.3, "tail_position": 0.9,
        },
        "material": "pla",
        "print_process": {
            "nozzle": 0.0004, "w_e": 0.00045, "layer_h": 0.0002,
            "build_volume": [0.22, 0.22, 0.25],
        },
        "propulsion": {
            "motor": {"P_max": 300.0, "mass": 0.05},
            "battery": {
                "cells_S": 3, "cells_P": 1, "capacity_Ah": 1.5,
                "voltage_nominal": 11.1, "mass": 0.12, "C_rate_max": 30.0,
            },
        },
    }
    schema = load_input(data)
    assert schema.mission.V_cruise == 15.0
'''.lstrip()


# I due test seguenti contengono ''' (fake modules): uso placeholder @TS@
FILES["rcsizer/tests/test_registry.py"] = r'''
"""Test di accettazione: un modulo finto si aggiunge solo con una cartella."""
import sys
from rcsizer.core.registry import ModuleRegistry
from rcsizer.core.state import new_state


_FAKE_MODULE = @TS@\
name = "fake_foo"
version = "0.1.0"
requires = ["input"]
provides = ["foo"]

def run(state):
    return state.with_derived("foo", x=42, label="hello")
@TS@


def _make_fake_package(root):
    pkg = root / "fake_modules"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    mod = pkg / "fake_foo"
    mod.mkdir()
    (mod / "__init__.py").write_text(_FAKE_MODULE, encoding="utf-8")
    return pkg


def test_fake_module_added_with_one_folder(tmp_path, monkeypatch, minimal_input):
    pkg_path = _make_fake_package(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        reg = ModuleRegistry()
        reg.discover("fake_modules")
        assert "fake_foo" in reg.modules
        iface = reg.modules["fake_foo"].interface
        assert iface.version == "0.1.0"
        assert iface.requires == ("input",)
        assert iface.provides == ("foo",)

        s = reg.get("fake_foo").run(new_state(minimal_input))
        assert s.derived["foo"]["x"] == 42
        assert s.derived["foo"]["label"] == "hello"
    finally:
        for k in list(sys.modules):
            if k.startswith("fake_modules"):
                del sys.modules[k]


def test_missing_interface_attrs_raises(tmp_path, monkeypatch):
    pkg = tmp_path / "bad_modules"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    mod = pkg / "bad"
    mod.mkdir()
    (mod / "__init__.py").write_text(
        "name='bad'\n# mancano version, requires, provides, run\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        reg = ModuleRegistry()
        reg.discover("bad_modules")
        assert "bad" not in reg.modules
    finally:
        for k in list(sys.modules):
            if k.startswith("bad_modules"):
                del sys.modules[k]
'''.lstrip()


FILES["rcsizer/tests/test_pipeline.py"] = r'''
"""Test di accettazione: pipeline con modulo finto che scrive nel proprio namespace."""
import sys
from pathlib import Path

from rcsizer.core.pipeline import Pipeline
from rcsizer.core.registry import ModuleRegistry
from rcsizer.core.state import new_state


_FAKE_A = @TS@\
name = "fake_a"
version = "0.1.0"
requires = ["input"]
provides = ["a"]
def run(state):
    return state.with_derived("a", val=1)
@TS@

_FAKE_B = @TS@\
name = "fake_b"
version = "0.1.0"
requires = ["a"]
provides = ["b"]
def run(state):
    return state.with_derived("b", val=state.derived["a"]["val"] + 1)
@TS@

_FAKE_CYCLE_1 = @TS@\
name = "cyc1"
version = "0.1.0"
requires = ["c"]
provides = ["a"]
def run(state):
    return state.with_derived("a", v=1)
@TS@

_FAKE_CYCLE_2 = @TS@\
name = "cyc2"
version = "0.1.0"
requires = ["a"]
provides = ["c"]
def run(state):
    return state.with_derived("c", v=state.derived.get("a", {}).get("v", 0) + 1)
@TS@


def _write_module(root: Path, pkg: str, modname: str, body: str):
    p = root / pkg
    p.mkdir(exist_ok=True)
    (p / "__init__.py").write_text("", encoding="utf-8")
    m = p / modname
    m.mkdir()
    (m / "__init__.py").write_text(body, encoding="utf-8")


def test_pipeline_runs_in_topological_order(tmp_path, monkeypatch, minimal_input):
    _write_module(tmp_path, "fake_mods", "fake_a", _FAKE_A)
    _write_module(tmp_path, "fake_mods", "fake_b", _FAKE_B)

    pipeline_yaml = tmp_path / "pipeline.yaml"
    pipeline_yaml.write_text(
        "pipeline:\n"
        "  - b: {impl: fake_b}\n"
        "  - a: {impl: fake_a}\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        reg = ModuleRegistry()
        reg.discover("fake_mods")
        pipe = Pipeline.from_file(reg, pipeline_yaml)
        assert pipe._order == ["fake_a", "fake_b"]
        out = pipe.run_once(new_state(minimal_input))
        assert out.derived["b"]["val"] == 2
    finally:
        for k in list(sys.modules):
            if k.startswith("fake_mods"):
                del sys.modules[k]


def test_pipeline_falls_back_on_cycle(tmp_path, monkeypatch, minimal_input):
    _write_module(tmp_path, "cycle_mods", "cyc1", _FAKE_CYCLE_1)
    _write_module(tmp_path, "cycle_mods", "cyc2", _FAKE_CYCLE_2)

    pipeline_yaml = tmp_path / "pipeline.yaml"
    pipeline_yaml.write_text(
        "pipeline:\n"
        "  - a: {impl: cyc1}\n"
        "  - b: {impl: cyc2}\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        reg = ModuleRegistry()
        reg.discover("cycle_mods")
        pipe = Pipeline.from_file(reg, pipeline_yaml)
        assert pipe._order == ["cyc1", "cyc2"]
        out = pipe.run_once(new_state(minimal_input))
        assert "a" in out.derived and "c" in out.derived
    finally:
        for k in list(sys.modules):
            if k.startswith("cycle_mods"):
                del sys.modules[k]


def test_pipeline_requires_unsatisfied_raises(tmp_path, monkeypatch, minimal_input):
    _write_module(tmp_path, "lonely_mods", "lonely",
                  'name="lonely"\nversion="0.1.0"\nrequires=["nope"]\nprovides=["x"]\n'
                  'def run(state): return state\n')
    pipeline_yaml = tmp_path / "pipeline.yaml"
    pipeline_yaml.write_text("pipeline:\n  - x: {impl: lonely}\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        reg = ModuleRegistry()
        reg.discover("lonely_mods")
        pipe = Pipeline.from_file(reg, pipeline_yaml)
        import pytest
        with pytest.raises(ValueError, match="nope"):
            pipe.run_once(new_state(minimal_input))
    finally:
        for k in list(sys.modules):
            if k.startswith("lonely_mods"):
                del sys.modules[k]
'''.lstrip()


# Input di esempio
FILES["input_trainer.json"] = r'''
{
  "aircraft_type": "trainer",
  "mission": {
    "V_cruise": 15.0,
    "altitude_ops": 100.0,
    "takeoff_mode": "hand_launch",
    "n_limit_target": 4.5
  },
  "wing": {
    "panels": [{
      "span": 0.5,
      "chord_root": 0.25,
      "chord_tip": 0.18,
      "sweep_LE": 0.0,
      "airfoil_root": "NACA2412",
      "airfoil_tip": "NACA2412"
    }]
  },
  "tail": { "tail_config": "conventional" },
  "fuselage": {
    "L_f": 1.0,
    "sections": [
      { "x": 0.0, "width": 0.10, "height": 0.12 },
      { "x": 1.0, "width": 0.05, "height": 0.06 }
    ],
    "wing_position": 0.3,
    "tail_position": 0.9
  },
  "material": "pla",
  "print_process": {
    "nozzle": 0.0004,
    "w_e": 0.00045,
    "layer_h": 0.0002,
    "build_volume": [0.22, 0.22, 0.25]
  },
  "propulsion": {
    "motor": { "P_max": 300.0, "mass": 0.05 },
    "battery": {
      "cells_S": 3, "cells_P": 1,
      "capacity_Ah": 1.5, "voltage_nominal": 11.1,
      "mass": 0.12, "C_rate_max": 30.0
    }
  }
}
'''.lstrip()


# ============================================================================
# LOGICA DI BOOTSTRAP
# ============================================================================

def _expand_placeholders():
    """Sostituisce @TS@ con ''' nei file problematici."""
    for k, v in list(FILES.items()):
        if "@TS@" in v:
            FILES[k] = v.replace("@TS@", "'''")


def write_files(root: Path) -> None:
    print("=" * 60)
    print("1/4  Creazione struttura e file...")
    print("=" * 60)
    for rel_path, content in FILES.items():
        p = root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            print(f"  [sovrascrivo] {rel_path}")
        else:
            print(f"  [nuovo]        {rel_path}")
        p.write_text(content, encoding="utf-8")
    print(f"\n  Totale: {len(FILES)} file scritti.")


def setup_venv(root: Path) -> Path:
    print("\n" + "=" * 60)
    print("2/4  Ambiente virtuale...")
    print("=" * 60)
    venv = root / ".venv"
    if venv.exists():
        print(f"  .venv/ esiste già, salto.")
    else:
        print(f"  Creo .venv/ con {sys.executable}")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
        print("  Fatto.")
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def pip_install(root: Path, venv_python: Path) -> None:
    print("\n" + "=" * 60)
    print("3/4  Installazione dipendenze (pydantic, pyyaml, pytest)...")
    print("=" * 60)
    print("  Questo può richiedere 1-2 minuti la prima volta.")
    subprocess.check_call(
        [str(venv_python), "-m", "pip", "install", "--quiet",
         "--disable-pip-version-check", "-e", str(root)]
    )
    print("  Installazione completata.")


def run_tests(venv_python: Path) -> bool:
    print("\n" + "=" * 60)
    print("4/4  Esecuzione test di accettazione...")
    print("=" * 60)
    result = subprocess.run(
        [str(venv_python), "-m", "pytest", "-q"],
        cwd=None,
    )
    return result.returncode == 0


def main() -> int:
    root = Path.cwd()

    if not (root / "bootstrap.py").exists():
        print("ERRORE: devi eseguire questo script dentro la cartella che contiene bootstrap.py.")
        print(f"Cartella corrente: {root}")
        return 1

    _expand_placeholders()
    write_files(root)
    venv_python = setup_venv(root)
    try:
        pip_install(root, venv_python)
    except subprocess.CalledProcessError as e:
        print(f"\nERRORE durante pip install: {e}")
        print("Suggerimenti:")
        print("  - Sei connesso a internet?")
        print("  - Hai Python 3.11+? Controlla con: python --version")
        return 1

    tests_ok = run_tests(venv_python)

    print("\n" + "=" * 60)
    if tests_ok:
        print("✅ BOOTSTRAP COMPLETATO")
        print("=" * 60)
        print("Tutti i test sono passati.")
    else:
        print("⚠️  BOOTSTRAP COMPLETATO CON ERRORI NEI TEST")
        print("=" * 60)
        print("I file sono stati creati, ma alcuni test falliscono.")
        print("Controlla l'output sopra per capire cosa non va.")
    print()
    print("Prossimi passi:")
    print("  1. Apri la cartella in VS Code: File -> Open Folder...")
    print("  2. Seleziona l'interprete: Ctrl+Shift+P -> 'Python: Select Interpreter'")
    print("     e scegli .venv")
    print("  3. (Opzionale) Genera schema.json:")
    if os.name == "nt":
        print("       .venv\\Scripts\\python scripts\\generate_schema.py")
    else:
        print("       .venv/bin/python scripts/generate_schema.py")
    print("  4. (Opzionale) Prova la CLI:")
    if os.name == "nt":
        print("       .venv\\Scripts\\python -m rcsizer input_trainer.json")
    else:
        print("       .venv/bin/python -m rcsizer input_trainer.json")
    print()
    return 0 if tests_ok else 1


if __name__ == "__main__":
    sys.exit(main())
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


class InternalStructureInput(BaseModel):
    model_config = _FROZEN
    carbon_tube_outer_d: Length = Field(default=0.0, ge=0)
    carbon_tube_inner_d: Length = Field(default=0.0, ge=0)
    truss_angle: Angle = Field(default=45.0 * 3.14159 / 180.0)

class WingInput(BaseModel):
    model_config = _FROZEN
    panels: list[PanelInput] = Field(min_length=1)
    wing_airfoil: Optional[str] = None
    wing_position_z: WingPositionZ = WingPositionZ.MID
    control_surfaces: list[ControlSurfaceInput] = Field(default_factory=list)
    fillet_wing_fuselage: bool = False
    winglets: bool = False
    internal_structure: Optional[InternalStructureInput] = Field(default=None) # <-- AGGIUNTO
    W_S_target: float = Field(default=60.0, gt=0, description="Carico alare target [N/m2]")
    AR_target: float = Field(default=6.0, gt=0, description="Allungamento alare target")


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
    source: Optional[str] = None


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

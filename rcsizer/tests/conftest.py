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

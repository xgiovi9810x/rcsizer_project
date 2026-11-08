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

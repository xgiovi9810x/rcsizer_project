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
        sweep_LE=0.0,
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

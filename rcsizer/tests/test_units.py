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

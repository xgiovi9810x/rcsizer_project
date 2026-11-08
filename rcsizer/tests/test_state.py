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

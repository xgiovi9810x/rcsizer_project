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

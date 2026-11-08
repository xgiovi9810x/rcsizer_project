"""Test di accettazione: pipeline con modulo finto che scrive nel proprio namespace."""
import sys
from pathlib import Path

from rcsizer.core.pipeline import Pipeline
from rcsizer.core.registry import ModuleRegistry
from rcsizer.core.state import new_state


_FAKE_A = '''\
name = "fake_a"
version = "0.1.0"
requires = ["input"]
provides = ["a"]
def run(state):
    return state.with_derived("a", val=1)
'''

_FAKE_B = '''\
name = "fake_b"
version = "0.1.0"
requires = ["a"]
provides = ["b"]
def run(state):
    return state.with_derived("b", val=state.derived["a"]["val"] + 1)
'''

_FAKE_CYCLE_1 = '''\
name = "cyc1"
version = "0.1.0"
requires = ["c"]
provides = ["a"]
def run(state):
    return state.with_derived("a", v=1)
'''

_FAKE_CYCLE_2 = '''\
name = "cyc2"
version = "0.1.0"
requires = ["a"]
provides = ["c"]
def run(state):
    return state.with_derived("c", v=state.derived.get("a", {}).get("v", 0) + 1)
'''


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

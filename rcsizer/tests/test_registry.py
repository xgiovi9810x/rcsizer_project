"""Test di accettazione: un modulo finto si aggiunge solo con una cartella."""
import sys
from rcsizer.core.registry import ModuleRegistry
from rcsizer.core.state import new_state


_FAKE_MODULE = '''\
name = "fake_foo"
version = "0.1.0"
requires = ["input"]
provides = ["foo"]

def run(state):
    return state.with_derived("foo", x=42, label="hello")
'''


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

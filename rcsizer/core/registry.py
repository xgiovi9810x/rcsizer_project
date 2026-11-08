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

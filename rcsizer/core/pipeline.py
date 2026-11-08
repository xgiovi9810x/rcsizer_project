"""Motore di pipeline: legge pipeline.yaml, risolve l'ordine, esegue."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional
import yaml
from pydantic import BaseModel, ConfigDict, Field

from .state import DesignState, Warning
from .registry import ModuleRegistry


class PipelineStage(BaseModel):
    model_config = ConfigDict(extra="allow")
    impl: str


class LoopConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variables: list[str] = Field(default_factory=list)
    tolerance: dict[str, float] = Field(default_factory=dict)
    max_iter: int = 30


class PipelineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pipeline: list[dict[str, PipelineStage]]
    loop: Optional[LoopConfig] = None


class Pipeline:
    def __init__(self, registry: ModuleRegistry, config: PipelineConfig) -> None:
        self.registry = registry
        self.config = config
        self._stages: list[tuple[str, str]] = self._parse_stages()
        self._order: list[str] = self._resolve_order()

    def _parse_stages(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for entry in self.config.pipeline:
            if len(entry) != 1:
                raise ValueError(f"Ogni stage deve avere una sola chiave, trovato: {entry}")
            (stage_name, cfg), = entry.items()
            out.append((stage_name, cfg.impl))
        return out

    def _resolve_order(self) -> list[str]:
        impl_names = [impl for _, impl in self._stages]
        field_to_impl: dict[str, str] = {}
        for impl in impl_names:
            reg = self.registry.get(impl)
            for f in reg.interface.provides:
                field_to_impl[f] = impl

        deps: dict[str, set[str]] = {impl: set() for impl in impl_names}
        for impl in impl_names:
            reg = self.registry.get(impl)
            for f in reg.interface.requires:
                if f in field_to_impl and field_to_impl[f] != impl:
                    deps[impl].add(field_to_impl[f])

        try:
            ordered: list[str] = []
            visited: set[str] = set()
            visiting: set[str] = set()

            def visit(n: str) -> None:
                if n in visited:
                    return
                if n in visiting:
                    raise ValueError(f"Dipendenza ciclica su '{n}'")
                visiting.add(n)
                for d in deps[n]:
                    visit(d)
                visiting.discard(n)
                visited.add(n)
                ordered.append(n)

            for impl in impl_names:
                visit(impl)
            return ordered
        except ValueError:
            return impl_names

    def _validate_requires(self) -> None:
        required: set[str] = set()
        provided: set[str] = {"input"}
        for _, impl in self._stages:
            reg = self.registry.get(impl)
            required.update(reg.interface.requires)
            provided.update(reg.interface.provides)
        missing = required - provided
        if missing:
            raise ValueError(f"Campi richiesti non forniti da alcun modulo: {sorted(missing)}")

    def run_once(self, state: DesignState) -> DesignState:
        self._validate_requires()
        for impl in self._order:
            state = self.registry.get(impl).run(state)
        return state

    def run(self, state: DesignState) -> DesignState:
        if self.config.loop is None:
            return self.run_once(state)
        return self._run_fixed_point(state, self.config.loop)

    def _run_fixed_point(self, state: DesignState, loop: LoopConfig) -> DesignState:
        prev_vals: dict[str, float] = {}
        for it in range(loop.max_iter):
            state = self.run_once(state).with_iteration(it)
            cur_vals: dict[str, float] = {}
            for var in loop.variables:
                v = self._read_var(state, var)
                if isinstance(v, (int, float)):
                    cur_vals[var] = float(v)
            if it > 0 and self._converged(prev_vals, cur_vals, loop.tolerance):
                return state
            prev_vals = cur_vals
        state = state.with_warning(Warning(
            code="pipeline.max_iter",
            severity="warning",
            message=f"Pipeline non convergente in {loop.max_iter} iterazioni",
        ))
        return state

    @staticmethod
    def _read_var(state: DesignState, var: str) -> Any:
        parts = var.split(".")
        if len(parts) == 2:
            ns, key = parts
            return state.derived.get(ns, {}).get(key)
        return None

    @staticmethod
    def _converged(prev: dict[str, float], cur: dict[str, float],
                   tol: dict[str, float]) -> bool:
        for k, v_cur in cur.items():
            if k not in prev:
                return False
            denom = max(abs(prev[k]), 1e-9)
            if abs(v_cur - prev[k]) / denom > tol.get(k, 1e-3):
                return False
        return True

    @classmethod
    def from_file(cls, registry: ModuleRegistry, path: str | Path) -> "Pipeline":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(registry, PipelineConfig.model_validate(data))

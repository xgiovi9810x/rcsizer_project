"""DesignState: stato immutabile della pipeline, serializzabile in JSON."""
from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from .schema import InputSchema


class ProvenanceKind(str, Enum):
    ANALYTIC = "A"
    EMPIRICAL = "E"
    INPUT = "I"
    DERIVED = "D"
    DEFAULT = "F"


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True)
    source: str
    kind: ProvenanceKind
    iteration: int = 0
    notes: str | None = None


class Warning(BaseModel):
    model_config = ConfigDict(frozen=True)
    code: str
    severity: str = "warning"
    message: str
    field: str | None = None
    iteration: int = 0


_FROZEN = ConfigDict(frozen=True, extra="forbid")


class DesignState(BaseModel):
    model_config = _FROZEN

    input: InputSchema
    derived: dict[str, dict[str, Any]] = Field(default_factory=dict)
    provenance: dict[str, Provenance] = Field(default_factory=dict)
    warnings: tuple[Warning, ...] = ()
    iteration: int = 0

    def with_derived(self, namespace: str, **kwargs: Any) -> "DesignState":
        new_derived = {k: dict(v) for k, v in self.derived.items()}
        new_derived.setdefault(namespace, {}).update(kwargs)
        return self.model_copy(update={"derived": new_derived})

    def with_provenance(self, path: str, prov: Provenance) -> "DesignState":
        new_prov = dict(self.provenance)
        new_prov[path] = prov
        return self.model_copy(update={"provenance": new_prov})

    def with_warning(self, w: Warning) -> "DesignState":
        return self.model_copy(update={"warnings": self.warnings + (w,)})

    def with_iteration(self, it: int) -> "DesignState":
        return self.model_copy(update={"iteration": it})

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, s: str) -> "DesignState":
        return cls.model_validate_json(s)


def new_state(validated: InputSchema) -> DesignState:
    return DesignState(input=validated)

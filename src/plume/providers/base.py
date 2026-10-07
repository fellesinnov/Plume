"""Normalized provider contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class ProviderContext:
    """Runtime context kept outside the portable provider descriptor."""

    config_dir: Path


@dataclass(frozen=True)
class ProviderProvenance:
    provider: str
    source: str
    request: Mapping[str, Any]
    input_sha256: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderResult:
    """Small model-facing data payload plus separate provenance."""

    data_kind: str
    records: tuple[Mapping[str, Any], ...]
    provenance: ProviderProvenance

    def manifest_summary(self) -> dict[str, Any]:
        return {
            "provider": self.provenance.provider,
            "data_kind": self.data_kind,
            "record_count": len(self.records),
            "source": self.provenance.source,
            "request": dict(self.provenance.request),
            "input_sha256": self.provenance.input_sha256,
            "warnings": list(self.provenance.warnings),
        }


class Provider(Protocol):
    name: str

    def normalize_spec(self, raw: Mapping[str, Any], *, context: str) -> dict[str, Any]: ...

    def load(self, spec: Mapping[str, Any], *, context: ProviderContext) -> ProviderResult: ...

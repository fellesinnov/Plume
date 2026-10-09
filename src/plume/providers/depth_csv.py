"""Read a single static water-column profile from a local UTF-8 CSV file."""
from __future__ import annotations

import csv
import hashlib
import io
import math
from pathlib import Path
from typing import Any, Mapping

from ..errors import ConfigError, ProviderDataError
from .base import ProviderContext, ProviderProvenance, ProviderResult


class CsvDepthProfileProvider:
    """Rows depth_m,value; no temporal interpolation and no network I/O."""

    name = "csv_depth_profile"

    def normalize_spec(self, raw: Mapping[str, Any], *, context: str) -> dict[str, Any]:
        unknown = set(raw) - {"provider", "path", "depth_column", "value_column"}
        if unknown:
            raise ConfigError(f"{context} has unsupported field(s): {', '.join(sorted(unknown))}")
        path = raw.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ConfigError(f"{context}.path must be a non-empty string")
        out = {"provider": self.name, "path": Path(path.strip().replace('\\', '/')).as_posix()}
        for key, default in (("depth_column", "depth_m"), ("value_column", "value")):
            name = raw.get(key, default)
            if not isinstance(name, str) or not name.strip():
                raise ConfigError(f"{context}.{key} must be a non-empty string")
            out[key] = name.strip()
        if out["depth_column"] == out["value_column"]:
            raise ConfigError(f"{context} depth and value columns must differ")
        return out

    def load(self, spec: Mapping[str, Any], *, context: ProviderContext) -> ProviderResult:
        configured = Path(str(spec["path"]))
        path = (configured if configured.is_absolute() else context.config_dir / configured).resolve()
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ProviderDataError(f"depth-profile CSV cannot be read: {path}") from exc
        try:
            reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
            required = (str(spec["depth_column"]), str(spec["value_column"]))
            if not all(key in (reader.fieldnames or ()) for key in required):
                raise ProviderDataError(f"depth-profile CSV is missing required columns: {required}")
            levels = []
            for lineno, row in enumerate(reader, 2):
                try:
                    depth = float(row[required[0]])
                    value = float(row[required[1]])
                except (TypeError, ValueError) as exc:
                    raise ProviderDataError(f"depth-profile CSV row {lineno} contains invalid numbers") from exc
                if (not math.isfinite(depth) or not math.isfinite(value) or depth < 0 or
                        (levels and depth <= levels[-1]["depth_m"])):
                    raise ProviderDataError(f"depth-profile CSV row {lineno} has invalid or non-increasing depth/value")
                levels.append({"depth_m": depth, "value": value})
        except UnicodeDecodeError as exc:
            raise ProviderDataError(f"depth-profile CSV must be UTF-8: {path}") from exc
        if len(levels) < 2:
            raise ProviderDataError("depth-profile CSV requires at least two rows")
        return ProviderResult(
            data_kind="depth_profile", records=tuple(levels),
            provenance=ProviderProvenance(provider=self.name, source=str(path),
                                          request=dict(spec), input_sha256=hashlib.sha256(raw).hexdigest()),
        )

"""Reference-evidence tooling for Plume REF-1.

This package is deliberately outside the future production Plume package. It parses and
normalizes immutable third-party evidence without creating a runtime dependency from the
product core back to the reference distributions.
"""

from .manifest import ManifestError, load_manifest, validate_manifest
from .plumes_dat import PlumesDat, parse_modelresults

__all__ = [
    "ManifestError",
    "PlumesDat",
    "load_manifest",
    "parse_modelresults",
    "validate_manifest",
]

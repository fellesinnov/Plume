"""Domain-specific errors exposed by the Plume core."""


class PlumeError(Exception):
    """Base class for expected Plume failures."""


class ConfigError(PlumeError):
    """Raised when a config cannot be parsed or normalized."""


class UnsupportedSchemaVersionError(ConfigError):
    """Raised when the config schema version is not implemented."""


class UnsupportedOutletError(ConfigError):
    """Raised when no outlet adapter is registered for a configured type."""


class UnsupportedProviderError(ConfigError):
    """Raised when no provider is registered for a descriptor."""


class ProviderDataError(PlumeError):
    """Raised when provider-backed data are missing or malformed."""


class WorkspaceError(PlumeError):
    """Raised when a workspace/run cannot be created safely."""


class ModelError(PlumeError):
    """Base class for near-field model failures."""


class ModelInputError(ModelError):
    """Raised when normalized model input is incomplete or non-physical."""


class UnsupportedModelOutletError(ModelError):
    """Raised when no near-field physics adapter implements a normalized outlet."""


class ThermodynamicsError(ModelError):
    """Raised when the production thermodynamic backend is unavailable or invalid."""

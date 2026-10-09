"""Provider registry and public provider contracts."""

from __future__ import annotations

from typing import Any, Mapping

from ..errors import ConfigError, UnsupportedProviderError
from .base import Provider, ProviderContext, ProviderProvenance, ProviderResult
from .builtin import ConstantProvider, ConstantVectorProvider, CsvProvider, InlineProfileProvider
from .depth_csv import CsvDepthProfileProvider
from .history_csv import CsvTimeDepthProfileProvider, CsvTimeVectorProfileProvider

_PROVIDERS: dict[str, Provider] = {
    provider.name: provider
    for provider in (
        ConstantProvider(),
        ConstantVectorProvider(),
        InlineProfileProvider(),
        CsvProvider(),
        CsvDepthProfileProvider(),
        CsvTimeDepthProfileProvider(),
        CsvTimeVectorProfileProvider(),
    )
}


def register_provider(provider: Provider) -> None:
    if not provider.name:
        raise ValueError("provider.name must be non-empty")
    _PROVIDERS[provider.name] = provider


def normalize_provider_spec(raw: Mapping[str, Any], *, context: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ConfigError(f"{context} must be a provider mapping")
    provider_name = raw.get("provider")
    if not isinstance(provider_name, str) or not provider_name:
        raise ConfigError(f"{context}.provider must be a non-empty string")
    provider = _PROVIDERS.get(provider_name)
    if provider is None:
        supported = ", ".join(sorted(_PROVIDERS))
        raise UnsupportedProviderError(
            f"unsupported provider {provider_name!r} at {context}; supported: {supported}"
        )
    return provider.normalize_spec(raw, context=context)


def load_provider(spec: Mapping[str, Any], *, context: ProviderContext) -> ProviderResult:
    provider_name = str(spec["provider"])
    provider = _PROVIDERS.get(provider_name)
    if provider is None:
        raise UnsupportedProviderError(f"unsupported normalized provider {provider_name!r}")
    return provider.load(spec, context=context)


def supported_provider_names() -> tuple[str, ...]:
    return tuple(sorted(_PROVIDERS))


__all__ = [
    "ProviderContext",
    "ProviderProvenance",
    "ProviderResult",
    "load_provider",
    "normalize_provider_spec",
    "register_provider",
    "supported_provider_names",
]

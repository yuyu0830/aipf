from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aipf.providers.base import Provider, ProviderError, ProviderErrorCode
from aipf.providers.mock import MockProvider
from aipf.providers.ollama import OllamaProvider
from aipf.providers.openai_compatible import OpenAICompatibleProvider


ProviderFactory = Callable[[dict[str, Any]], Provider]


class ProviderRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, ProviderFactory] = {}

    def register(self, name: str, factory: ProviderFactory) -> None:
        if not name or name in self._factories:
            raise ValueError(f"provider already registered or invalid: {name}")
        self._factories[name] = factory

    def create(self, name: str, config: dict[str, Any] | None = None) -> Provider:
        try:
            factory = self._factories[name]
        except KeyError as exc:
            raise ProviderError(ProviderErrorCode.CONFIGURATION, f"unknown provider: {name}") from exc
        try:
            return factory(config or {})
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(ProviderErrorCode.CONFIGURATION, f"invalid {name} provider configuration: {exc}") from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))


def default_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register("mock", lambda config: MockProvider())
    registry.register(
        "ollama",
        lambda config: OllamaProvider(
            base_url=str(config.get("base_url", "http://127.0.0.1:11434")),
            timeout=int(config.get("timeout", 120)),
        ),
    )
    registry.register(
        "openai_compatible",
        lambda config: OpenAICompatibleProvider(
            base_url=str(config["base_url"]),
            api_key_env=str(config.get("api_key_env", "OPENAI_API_KEY")),
            timeout=int(config.get("timeout", 120)),
        ),
    )
    return registry

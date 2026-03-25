from __future__ import annotations

from collections.abc import Iterable

from crane.providers.base import PaperProvider, UnifiedMetadata


class ProviderRegistry:
    def __init__(self, providers: Iterable[PaperProvider] | None = None):
        self._providers: dict[str, PaperProvider] = {}
        for provider in providers or []:
            self.register(provider)

    def register(self, provider: PaperProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> PaperProvider | None:
        return self._providers.get(name)

    def list_names(self) -> list[str]:
        return list(self._providers)

    def search_all(
        self,
        query: str,
        max_results: int = 10,
        provider_names: list[str] | None = None,
    ) -> list[UnifiedMetadata]:
        results: list[UnifiedMetadata] = []
        for provider in self._iter_selected(provider_names):
            results.extend(provider.search(query, max_results=max_results))
        return results

    def _iter_selected(self, provider_names: list[str] | None = None) -> Iterable[PaperProvider]:
        if provider_names is None:
            return self._providers.values()

        selected: list[PaperProvider] = []
        for name in provider_names:
            provider = self.get(name)
            if provider is None:
                raise KeyError(f"Provider not registered: {name}")
            selected.append(provider)
        return selected

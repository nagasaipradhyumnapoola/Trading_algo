"""Model capability registry.

Maps logical tiers/routes to concrete FreeLLMAPI models and their measured
capabilities + health. Loaded from configuration/env, NOT hard-coded in agents.
The gateway selects a route by matching a task policy against this registry
(capability + health + cost + data classification).
"""

from __future__ import annotations

from .contracts import DataClass, ModelRoute


class ModelCapabilityRegistry:
    """In-memory registry. Phase 3 loads entries from config/env and health checks."""

    def __init__(self) -> None:
        self._routes: dict[str, ModelRoute] = {}

    def register(self, route: ModelRoute) -> None:
        self._routes[route.name] = route

    def get(self, name: str) -> ModelRoute | None:
        return self._routes.get(name)

    def healthy_routes(self, max_data_class: DataClass) -> list[ModelRoute]:
        """Healthy routes permitted for a given data classification."""
        order = {DataClass.PUBLIC: 0, DataClass.INTERNAL: 1, DataClass.USER: 2}
        cap = order[max_data_class]
        # a route cleared for a higher sensitivity can also handle lower — permitted >= required
        return [
            r for r in self._routes.values()
            if r.healthy and order[r.permitted_data_classification] >= cap
        ]

    def resolve(self, allowed_routes: list[str], max_data_class: DataClass) -> ModelRoute | None:
        """First allowed route that is registered, healthy, and cleared for the data. None -> degraded."""
        for name in allowed_routes:
            route = self._routes.get(name)
            if route and route.healthy:
                order = {DataClass.PUBLIC: 0, DataClass.INTERNAL: 1, DataClass.USER: 2}
                if order[route.permitted_data_classification] >= order[max_data_class]:
                    return route
        return None


def build_default_registry() -> ModelCapabilityRegistry:
    """Placeholder registry. Phase 3 populates concrete models from env/config."""
    return ModelCapabilityRegistry()

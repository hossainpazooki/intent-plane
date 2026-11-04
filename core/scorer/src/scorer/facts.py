"""Fact sources (CONTRACT.md §8).

StaticFactSource is both the test double and the demo configuration. A live
fact source is loaded at boot through SCORER_FACTS_MODULE (see __main__) and
receives the static map as its fallback; the service itself ships none.
"""

from typing import Protocol


class FactSource(Protocol):
    def get(self, criterion: str, intent_id: str) -> float | None: ...


class StaticFactSource:
    """Immutable criterion -> fact map; unknown criterion yields None."""

    def __init__(self, facts: dict[str, float]) -> None:
        self._facts = dict(facts)

    def get(self, criterion: str, intent_id: str) -> float | None:
        return self._facts.get(criterion)

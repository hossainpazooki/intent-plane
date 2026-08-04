"""Fact sources (CONTRACT.md §8).

StaticFactSource is both the test double and the demo configuration. A live
fact source is a LATER slice — do not fake one.
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

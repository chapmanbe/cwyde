"""
ReasonerStrategy Protocol and implementations.

Default usage: CompositeStrategy(GamenStrategy(), FallbackStrategy())
  — try gamen-validate for formal reasoning; fall back on infrastructure failures.
  — NEVER fall back on GamenSemanticError (that indicates a translator bug).

Users requiring hard-failure on missing binary pass GamenStrategy() directly.
Users requiring pure-Python pass FallbackStrategy() directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from cwyde.categories import AssertionCategory
from cwyde.exceptions import GamenError, GamenSemanticError

if TYPE_CHECKING:
    from cwyde.formal.modal import ModalFormula


@runtime_checkable
class ReasonerStrategy(Protocol):
    def is_available(self) -> bool: ...
    def check_consistency(self, formulas: list["ModalFormula"]) -> "ConsistencyResult": ...
    def resolve_conflict(self, modifiers: list[AssertionCategory]) -> AssertionCategory: ...


class ConsistencyResult:
    def __init__(self, consistent: bool | None, explanation: str = ""):
        self.consistent = consistent
        self.explanation = explanation

    def __repr__(self):
        return f"ConsistencyResult(consistent={self.consistent!r})"


class FallbackStrategy:
    """Pure-Python YAML-table interpreter. Always available."""

    def __init__(self, rules=None):
        self._rules = rules  # InteractionRulesFile, loaded lazily

    def is_available(self) -> bool:
        return True

    def _ensure_rules(self):
        if self._rules is None:
            from cwyde_knowledge import default_interaction_rules
            self._rules = default_interaction_rules()

    def check_consistency(self, formulas: list) -> ConsistencyResult:
        # Fallback cannot do full modal consistency — returns None (unknown)
        return ConsistencyResult(consistent=None, explanation="gamen-validate not available; consistency unknown")

    def resolve_conflict(self, modifiers: list[AssertionCategory]) -> AssertionCategory:
        self._ensure_rules()
        modifier_set = set(modifiers)

        # Check explicit override entries first
        for entry in self._rules.overrides:
            if set(entry.modifiers) == modifier_set:
                if entry.submit_to_gamen:
                    return AssertionCategory.UNRESOLVED
                return entry.result

        # Check unresolvable combinations
        for combo in self._rules.unresolvable:
            if set(combo) == modifier_set:
                return AssertionCategory.UNRESOLVED

        # Fall through to precedence list
        for cat in self._rules.precedence:
            if cat in modifier_set:
                return cat

        return AssertionCategory.UNRESOLVED


class GamenStrategy:
    """Uses gamen-validate binary for formal reasoning. Raises on unavailability."""

    def __init__(self, bridge=None):
        self._bridge = bridge  # GamenBridge, lazy-init on first use

    def is_available(self) -> bool:
        try:
            self._ensure_bridge()
            return self._bridge.ping()
        except Exception:
            return False

    def _ensure_bridge(self):
        if self._bridge is None:
            from cwyde_haskell_bridge import GamenBridge
            self._bridge = GamenBridge()

    def check_consistency(self, formulas: list) -> ConsistencyResult:
        self._ensure_bridge()
        result = self._bridge.check_consistency(formulas)
        return ConsistencyResult(consistent=result.consistent, explanation=result.explanation)

    def resolve_conflict(self, modifiers: list[AssertionCategory]) -> AssertionCategory:
        # Conflict resolution via gamen requires translating modifiers to formulas
        # and asking for consistency — if inconsistent, return UNRESOLVED
        # Full implementation in section_propagator uses this path
        raise NotImplementedError("GamenStrategy.resolve_conflict requires entity atom context")


class CompositeStrategy:
    """Try gamen; fall back to YAML table on infrastructure failures.

    Falls back on: GamenBinaryNotFound, GamenTimeout, GamenInvocationError.
    Does NOT fall back on GamenSemanticError — that is a translator bug.
    """

    def __init__(self, primary: GamenStrategy, fallback: FallbackStrategy):
        self._primary = primary
        self._fallback = fallback

    def is_available(self) -> bool:
        return self._primary.is_available() or self._fallback.is_available()

    def check_consistency(self, formulas: list) -> ConsistencyResult:
        try:
            return self._primary.check_consistency(formulas)
        except GamenSemanticError:
            raise  # translator bug — surface immediately
        except GamenError:
            return self._fallback.check_consistency(formulas)

    def resolve_conflict(self, modifiers: list[AssertionCategory]) -> AssertionCategory:
        # For conflict resolution, gamen strategy needs extra context (entity atom)
        # so we route directly through fallback at this layer; gamen is invoked
        # from consistency_checker component which has the full formula context.
        return self._fallback.resolve_conflict(modifiers)


def default_strategy() -> CompositeStrategy:
    return CompositeStrategy(GamenStrategy(), FallbackStrategy())

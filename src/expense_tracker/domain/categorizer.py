"""The categorizer port: the only swappable dependency of the domain.

Implementations: a keyword-based fake (tests, CI, default) and, later,
an LLM-backed adapter. See docs/adr/0001.
"""

from typing import Protocol


class Categorizer(Protocol):
    """Suggests a category for an expense description.

    Returns a category name or None. Must not raise: a categorizer that
    cannot answer returns None. The domain maps any value outside the
    category list to the fallback category.
    """

    def suggest(self, description: str) -> str | None: ...

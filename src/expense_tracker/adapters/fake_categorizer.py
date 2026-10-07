"""Keyword-based categorizer: deterministic, offline, no API key.

The default categorizer of the server and the one used in tests and
CI. It implements the domain's `Categorizer` port.
"""

import re

KEYWORDS: dict[str, str] = {
    "coffee": "food",
    "cafe": "food",
    "restaurant": "food",
    "groceries": "food",
    "lunch": "food",
    "dinner": "food",
    "train": "transport",
    "bus": "transport",
    "taxi": "transport",
    "metro": "transport",
    "fuel": "transport",
    "rent": "housing",
    "mortgage": "housing",
    "electricity": "utilities",
    "water": "utilities",
    "internet": "utilities",
    "phone": "utilities",
    "pharmacy": "health",
    "doctor": "health",
    "dentist": "health",
    "cinema": "leisure",
    "concert": "leisure",
    "museum": "leisure",
    "clothes": "shopping",
    "shoes": "shopping",
    "books": "shopping",
}

WORD = re.compile(r"[a-z]+")


class FakeCategorizer:
    """Returns the category of the first keyword found as a word."""

    def suggest(self, description: str) -> str | None:
        for word in WORD.findall(description.lower()):
            if word in KEYWORDS:
                return KEYWORDS[word]
        return None

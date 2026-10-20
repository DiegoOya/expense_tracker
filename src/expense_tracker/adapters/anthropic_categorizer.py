"""Categorizer backed by Claude through the Anthropic API (opt-in).

Implements the domain's `Categorizer` port. Only the description and
the category list are sent; one attempt with a 10-second timeout. Any
failure is reported on stderr and the keyword fallback decides
instead, so `suggest` never raises. See specs/llm-categorizer and
docs/adr/0005.
"""

import json
import sys

import anthropic

from expense_tracker.domain.categorizer import Categorizer
from expense_tracker.domain.model import CATEGORIES

MODEL = "claude-haiku-5-5"
TIMEOUT_SECONDS = 10.0
MAX_TOKENS = 64
INVALID_ANSWER = "invalid answer"

SYSTEM_PROMPT = (
    "You classify one personal expense from its description. Answer "
    "with the single best category among: "
    + ", ".join(CATEGORIES)
    + ". Answer other when none of the others fits."
)

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(CATEGORIES)},
    },
    "required": ["category"],
    "additionalProperties": False,
}


class AnthropicCategorizer:
    """Asks Claude for the category; keywords decide when it fails."""

    def __init__(
        self, client: anthropic.Anthropic, fallback: Categorizer
    ) -> None:
        self.client = client
        self.fallback = fallback

    def suggest(self, description: str) -> str | None:
        try:
            response = self.client.with_options(
                timeout=TIMEOUT_SECONDS, max_retries=0
            ).messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                thinking={"type": "disabled"},
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": description}],
                output_config={
                    "format": {"type": "json_schema", "schema": ANSWER_SCHEMA}
                },
            )
            stop_reason = response.stop_reason
            text = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
        except anthropic.APIError as error:
            return self._fall_back(type(error).__name__, description)
        except (ValueError, TypeError, AttributeError):
            # A success reply whose body is not a message: the SDK's
            # JSON parsing (ValueError) or reading its fields fails
            # (AC-LLM-15).
            return self._fall_back(INVALID_ANSWER, description)

        if stop_reason in ("refusal", "max_tokens"):
            return self._fall_back(stop_reason, description)
        category = _category_in(text)
        if category is None:
            return self._fall_back(INVALID_ANSWER, description)
        return category

    def _fall_back(self, reason: str, description: str) -> str | None:
        # sys.stderr is looked up here, not bound at import, so pytest's
        # capture sees it; stdout carries the MCP protocol.
        print(
            f"llm categorizer failed: {reason}; using keywords",
            file=sys.stderr,
        )
        return self.fallback.suggest(description)


def _category_in(text: str) -> str | None:
    """The category of a `{"category": "<name>"}` answer, or None."""
    if not isinstance(text, str):
        # A broken endpoint can send a non-string text (5, null).
        return None
    try:
        answer = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(answer, dict):
        return None
    category = answer.get("category")
    return category if category in CATEGORIES else None

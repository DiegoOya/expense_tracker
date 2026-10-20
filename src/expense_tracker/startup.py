"""Startup configuration: which categorizer the server uses.

EXPENSE_TRACKER_CATEGORIZER chooses it (specs/llm-categorizer). The
keyword categorizer is the default and needs neither the Anthropic SDK
nor credentials, so the SDK is imported only when it is chosen: it is
the optional `llm` extra.
"""

from collections.abc import Mapping
from typing import TYPE_CHECKING

from expense_tracker.adapters.fake_categorizer import FakeCategorizer
from expense_tracker.domain.categorizer import Categorizer

if TYPE_CHECKING:
    # For the annotation only; httpx2 comes with the optional SDK.
    import httpx2

CATEGORIZER_VARIABLE = "EXPENSE_TRACKER_CATEGORIZER"
UNKNOWN_CATEGORIZER = (
    "EXPENSE_TRACKER_CATEGORIZER must be one of: keywords, anthropic"
)
MISSING_LLM_EXTRA = (
    "EXPENSE_TRACKER_CATEGORIZER=anthropic needs the llm extra "
    "(pip install -e '.[llm]')"
)
MISSING_CREDENTIALS = (
    "EXPENSE_TRACKER_CATEGORIZER=anthropic needs Anthropic credentials "
    "(ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or an ant auth profile)"
)


class ConfigurationError(Exception):
    """The server cannot start; the message says why."""


def choose_categorizer(
    environ: Mapping[str, str], http_client: "httpx2.Client | None" = None
) -> Categorizer:
    """The categorizer EXPENSE_TRACKER_CATEGORIZER asks for.

    Raises ConfigurationError for an unknown value, a missing SDK or
    missing credentials, checked in that order. The SDK reads the
    credentials from the process environment; `environ` only carries
    our own variable. `http_client` lets tests simulate the API.
    """
    value = environ.get(CATEGORIZER_VARIABLE, "").strip().lower()
    if value in ("", "keywords"):
        return FakeCategorizer()
    if value != "anthropic":
        raise ConfigurationError(UNKNOWN_CATEGORIZER)

    try:
        import anthropic
    except ImportError:
        raise ConfigurationError(MISSING_LLM_EXTRA) from None
    # Outside the try: an import error in our own adapter is a bug,
    # not a missing extra.
    from expense_tracker.adapters.anthropic_categorizer import (
        AnthropicCategorizer,
    )

    try:
        client = anthropic.Anthropic(http_client=http_client)
    except anthropic.AnthropicError:
        # E.g. a selected ant auth profile that does not exist.
        raise ConfigurationError(MISSING_CREDENTIALS) from None
    if (
        client.api_key is None
        and client.auth_token is None
        and client.credentials is None
    ):
        raise ConfigurationError(MISSING_CREDENTIALS)
    return AnthropicCategorizer(client, FakeCategorizer())

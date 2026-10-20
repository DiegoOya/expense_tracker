"""The LLM categorizer adapter against a simulated Anthropic API.

Every client gets the FakeAnthropicAPI transport, so nothing reaches
the network. The fallback is the keyword categorizer, which files
"Train ticket to Example City" under "transport".
"""

import pytest
from conftest import (
    DUMMY_CREDENTIAL,
    FakeAnthropicAPI,
    Reply,
    answer,
    answer_text,
    connection_failure,
    http_status,
    message_with_text,
    raw_body,
    stop,
    time_out,
)

from expense_tracker.adapters.anthropic_categorizer import (
    AnthropicCategorizer,
)
from expense_tracker.adapters.fake_categorizer import FakeCategorizer

DESCRIPTION = "Train ticket to Example City"

CATEGORIES = [
    "food",
    "transport",
    "housing",
    "utilities",
    "health",
    "leisure",
    "shopping",
    "other",
]


def suggest(api: FakeAnthropicAPI) -> str | None:
    categorizer = AnthropicCategorizer(api.client(), FakeCategorizer())
    return categorizer.suggest(DESCRIPTION)


@pytest.mark.spec("AC-LLM-05")
@pytest.mark.parametrize("category", CATEGORIES)
def test_answer_from_the_list_is_the_suggestion(
    anthropic_api: FakeAnthropicAPI, category: str
) -> None:
    anthropic_api.reply = answer(category)

    assert suggest(anthropic_api) == category


@pytest.mark.spec("AC-LLM-06")
@pytest.mark.parametrize(
    "reply",
    [
        pytest.param(time_out(), id="timeout"),
        pytest.param(connection_failure(), id="connection-failure"),
        pytest.param(http_status(400), id="http-400"),
        pytest.param(http_status(401), id="http-401"),
        pytest.param(http_status(403), id="http-403"),
        pytest.param(http_status(404), id="http-404"),
        pytest.param(http_status(408), id="http-408"),
        pytest.param(http_status(429), id="http-429"),
        pytest.param(http_status(500), id="http-500"),
        pytest.param(http_status(529), id="http-529"),
        pytest.param(stop("refusal"), id="stop-refusal"),
        pytest.param(stop("max_tokens"), id="stop-max-tokens"),
        pytest.param(answer("pets"), id="answer-pets"),
        pytest.param(answer("Food"), id="answer-capitalised-food"),
        pytest.param(answer_text("leisure"), id="text-not-json"),
        pytest.param(
            answer_text('{"name": "leisure"}'), id="json-without-category"
        ),
    ],
)
def test_failing_api_falls_back_to_keywords(
    anthropic_api: FakeAnthropicAPI, reply: Reply
) -> None:
    anthropic_api.reply = reply

    assert suggest(anthropic_api) == "transport"


@pytest.mark.spec("AC-LLM-08")
@pytest.mark.parametrize(
    "reply",
    [
        pytest.param(time_out(), id="timeout"),
        pytest.param(connection_failure(), id="connection-failure"),
        pytest.param(http_status(408), id="http-408"),
        pytest.param(http_status(429), id="http-429"),
        pytest.param(http_status(500), id="http-500"),
        pytest.param(http_status(529), id="http-529"),
    ],
)
def test_retryable_failure_is_not_retried(
    anthropic_api: FakeAnthropicAPI, reply: Reply
) -> None:
    anthropic_api.reply = reply

    suggest(anthropic_api)

    assert len(anthropic_api.requests) == 1


@pytest.mark.spec("AC-LLM-09")
def test_every_part_of_the_request_timeout_is_ten_seconds(
    anthropic_api: FakeAnthropicAPI,
) -> None:
    anthropic_api.reply = answer("leisure")

    suggest(anthropic_api)

    assert anthropic_api.timeouts == [
        {"connect": 10.0, "read": 10.0, "write": 10.0, "pool": 10.0}
    ]


@pytest.mark.spec("AC-LLM-10")
@pytest.mark.parametrize(
    ("reply", "line"),
    [
        pytest.param(
            http_status(429),
            "llm categorizer failed: RateLimitError; using keywords",
            id="http-429",
        ),
        pytest.param(
            time_out(),
            "llm categorizer failed: APITimeoutError; using keywords",
            id="timeout",
        ),
        pytest.param(
            connection_failure(),
            "llm categorizer failed: APIConnectionError; using keywords",
            id="connection-failure",
        ),
        pytest.param(
            stop("refusal"),
            "llm categorizer failed: refusal; using keywords",
            id="stop-refusal",
        ),
        pytest.param(
            stop("max_tokens"),
            "llm categorizer failed: max_tokens; using keywords",
            id="stop-max-tokens",
        ),
        pytest.param(
            answer("pets"),
            "llm categorizer failed: invalid answer; using keywords",
            id="answer-pets",
        ),
        pytest.param(
            answer_text("leisure"),
            "llm categorizer failed: invalid answer; using keywords",
            id="text-not-json",
        ),
        pytest.param(
            answer_text('{"name": "leisure"}'),
            "llm categorizer failed: invalid answer; using keywords",
            id="json-without-category",
        ),
        pytest.param(
            raw_body(b"not json", "application/json"),
            "llm categorizer failed: invalid answer; using keywords",
            id="body-not-json",
        ),
        pytest.param(
            raw_body(b"{}", "application/json"),
            "llm categorizer failed: invalid answer; using keywords",
            id="body-empty-object",
        ),
        pytest.param(
            raw_body(b"<html>proxy</html>", "text/html"),
            "llm categorizer failed: invalid answer; using keywords",
            id="body-html-page",
        ),
        pytest.param(
            raw_body(message_with_text(5), "application/json"),
            "llm categorizer failed: invalid answer; using keywords",
            id="body-text-5",
        ),
        pytest.param(
            raw_body(message_with_text(None), "application/json"),
            "llm categorizer failed: invalid answer; using keywords",
            id="body-text-null",
        ),
    ],
)
def test_failure_writes_one_stderr_line_with_the_reason(
    anthropic_api: FakeAnthropicAPI,
    capsys: pytest.CaptureFixture[str],
    reply: Reply,
    line: str,
) -> None:
    anthropic_api.reply = reply

    suggest(anthropic_api)

    captured = capsys.readouterr()
    assert captured.err == line + "\n"
    assert DESCRIPTION not in captured.err
    assert DUMMY_CREDENTIAL not in captured.err
    assert captured.out == ""


@pytest.mark.spec("AC-LLM-11")
def test_successful_answer_writes_nothing_to_stderr(
    anthropic_api: FakeAnthropicAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    anthropic_api.reply = answer("leisure")

    assert suggest(anthropic_api) == "leisure"

    assert capsys.readouterr().err == ""


@pytest.mark.spec("AC-LLM-15")
@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        pytest.param(b"not json", "application/json", id="not-json"),
        pytest.param(b"{}", "application/json", id="empty-object"),
        pytest.param(b"<html>proxy</html>", "text/html", id="html-page"),
        pytest.param(message_with_text(5), "application/json", id="text-5"),
        pytest.param(
            message_with_text(None), "application/json", id="text-null"
        ),
    ],
)
def test_success_reply_that_is_not_a_message_falls_back_to_keywords(
    anthropic_api: FakeAnthropicAPI, body: bytes, content_type: str
) -> None:
    anthropic_api.reply = raw_body(body, content_type)

    assert suggest(anthropic_api) == "transport"

"""Startup checks of EXPENSE_TRACKER_CATEGORIZER, through main().

main() must exit with status 1 and write only the message to stderr.
The startup_env fixture also points the database at tmp_path and gives
an empty stdin, so a main() that does not exit (red step, regression)
neither touches the repository's data nor waits for input.
"""

import io
import sys
from pathlib import Path

import pytest

from expense_tracker.server import main

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


@pytest.fixture
def startup_env(
    clean_env: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "EXPENSE_TRACKER_DB", str(tmp_path / "data" / "expenses.db")
    )
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"")))


def assert_exits_with_message(
    capsys: pytest.CaptureFixture[str], message: str
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 1
    assert captured.err == message + "\n"
    assert captured.out == ""


@pytest.mark.spec("AC-LLM-12")
@pytest.mark.parametrize("value", ["openai", "llm", "anthropic-api"])
def test_unknown_categorizer_stops_startup(
    startup_env: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    value: str,
) -> None:
    monkeypatch.setenv("EXPENSE_TRACKER_CATEGORIZER", value)

    assert_exits_with_message(capsys, UNKNOWN_CATEGORIZER)


@pytest.mark.spec("AC-LLM-13")
def test_anthropic_without_the_sdk_stops_startup(
    startup_env: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("EXPENSE_TRACKER_CATEGORIZER", "anthropic")
    monkeypatch.setitem(sys.modules, "anthropic", None)

    assert_exits_with_message(capsys, MISSING_LLM_EXTRA)


@pytest.mark.spec("AC-LLM-14")
@pytest.mark.parametrize(
    "api_key",
    [None, ""],
    ids=["no-anthropic-variables", "empty-api-key"],
)
@pytest.mark.parametrize(
    "config_dir_exists",
    [False, True],
    ids=["config-dir-missing", "config-dir-empty"],
)
def test_anthropic_without_credentials_stops_startup(
    startup_env: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    api_key: str | None,
    config_dir_exists: bool,
) -> None:
    monkeypatch.setenv("EXPENSE_TRACKER_CATEGORIZER", "anthropic")
    if api_key is not None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", api_key)
    if config_dir_exists:
        (tmp_path / ".config" / "anthropic").mkdir(parents=True)

    assert_exits_with_message(capsys, MISSING_CREDENTIALS)

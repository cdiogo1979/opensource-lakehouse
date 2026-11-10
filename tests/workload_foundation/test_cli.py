"""Task arguments after ``--`` (workflow "args"), for Airflow runs and direct runs."""

import sys

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from notebooks.common import cli

STANDARD = ["--environment", "uat", "--config-dir", "/opt/lakehouse-bundle/configs"]


def test_without_extras_task_args_are_empty():
    args = cli.parse_args(STANDARD)
    assert (args.environment, args.config_dir, args.task_args) == ("uat", "/opt/lakehouse-bundle/configs", [])
    assert cli.task_args(STANDARD) == []


def test_extras_after_the_separator_are_returned_unchanged():
    argv = STANDARD + ["--", "--date", "2026-11-10", "two words", "--"]
    assert cli.parse_args(argv).task_args == ["--date", "2026-11-10", "two words", "--"]
    assert cli.task_args(argv) == ["--date", "2026-11-10", "two words", "--"]


def test_standard_arguments_are_still_validated():
    with pytest.raises(SystemExit):
        cli.parse_args(["--environment", "staging", "--", "--x"])
    with pytest.raises(SystemExit):
        cli.parse_args(["--unknown"])


def test_jupyter_has_no_task_arguments(monkeypatch):
    monkeypatch.setitem(sys.modules, "ipykernel", object())
    monkeypatch.setattr(sys, "argv", ["kernel", "--", "--date", "x"])
    assert cli.task_args() == []


ARGUMENT = st.text(st.characters(categories=("L", "N", "P", "S", "Zs")), min_size=1, max_size=20)


@settings(print_blob=True)
@given(after=st.lists(ARGUMENT, max_size=6))
def test_p5_everything_after_the_first_separator_is_the_task_args(after):
    assert cli.parse_args(STANDARD + ["--"] + after).task_args == after

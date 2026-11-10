"""Shared command-line argument parsing for environment-based Spark jobs."""

import argparse
import sys
from typing import Any, Optional

from .config_loader import SUPPORTED_ENVIRONMENTS

# Airflow passes a task's workflow "args" after this separator:
#   spark-submit job.py --environment uat --config-dir ... -- --date 2026-11-10
TASK_ARGS_SEPARATOR = "--"


def _split(argv: Optional[list]) -> tuple:
    """Split an argument list at the first ``--`` into (standard, task) arguments."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if TASK_ARGS_SEPARATOR in arguments:
        index = arguments.index(TASK_ARGS_SEPARATOR)
        return arguments[:index], arguments[index + 1 :]
    return arguments, []


def parse_args(argv: Any = None) -> argparse.Namespace:
    """Parse the standard environment and config-directory arguments.

    Args:
        argv: Optional argument list, primarily for direct invocation.

    Returns:
        Parsed environment and optional config directory, plus ``task_args``:
        the workflow task's arguments after ``--`` (empty when there are none).
    """
    standard, extra = _split(argv)
    parser = argparse.ArgumentParser(description="Run a Spark workload using an explicit environment config.")
    parser.add_argument(
        "--environment",
        required=True,
        choices=sorted(SUPPORTED_ENVIRONMENTS),
        help="Environment config to load; no default is selected.",
    )
    parser.add_argument(
        "--config-dir",
        default=None,
        help="Directory containing the selected YAML (default: repository configs/).",
    )
    args = parser.parse_args(standard)
    args.task_args = extra
    return args


def task_args(argv: Any = None) -> list:
    """The workflow task's arguments after ``--``; empty in Jupyter and for direct runs without them.

    Args:
        argv: Optional argument list; defaults to ``sys.argv[1:]``.

    Returns:
        The arguments after the first ``--``, unchanged.
    """
    if argv is None and "ipykernel" in sys.modules:
        return []
    return _split(argv)[1]

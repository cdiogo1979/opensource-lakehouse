"""Shared command-line argument parsing for environment-based Spark jobs."""

import argparse
from typing import Any

from config_loader import SUPPORTED_ENVIRONMENTS


def parse_args(argv: Any = None) -> argparse.Namespace:
    """Parse the standard environment and config-directory arguments.

    Args:
        argv: Optional argument list, primarily for direct invocation.

    Returns:
        Parsed environment and optional config directory.
    """
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
    return parser.parse_args(argv)

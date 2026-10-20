"""Shared import setup and reproducibility reporting for unit tests."""

import os
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "dags"))
sys.path.insert(0, str(REPOSITORY_ROOT / "notebooks" / "workload"))
sys.path.insert(0, str(REPOSITORY_ROOT / "notebooks" / "common"))
HYPOTHESIS_SEED = int(os.environ.get("HYPOTHESIS_SEED", "0"))


@pytest.fixture(scope="session", autouse=True)
def report_hypothesis_seed():
    """Print the fixed/configurable Hypothesis seed in pytest's captured output."""
    print(f"Hypothesis reproducibility seed: {HYPOTHESIS_SEED}")

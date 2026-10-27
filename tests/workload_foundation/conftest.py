"""Shared lightweight Spark API stubs for workload unit tests."""

import os
import sys
from pathlib import Path
from types import ModuleType

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


@pytest.fixture(autouse=True)
def stub_spark_current_timestamp(monkeypatch):
    """Provide the one PySpark expression used by the workload without Spark."""
    pyspark = ModuleType("pyspark")
    sql = ModuleType("pyspark.sql")
    functions = ModuleType("pyspark.sql.functions")

    def current_timestamp():
        return "current_timestamp_expression"

    functions.current_timestamp = current_timestamp
    pyspark.sql = sql
    sql.functions = functions
    monkeypatch.setitem(sys.modules, "pyspark", pyspark)
    monkeypatch.setitem(sys.modules, "pyspark.sql", sql)
    monkeypatch.setitem(sys.modules, "pyspark.sql.functions", functions)

"""generate_tpch.py: arguments, the TPC-H count rules (P6, P7), and a DuckDB run when duckdb is installed."""

import json
import os
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given, seed, settings, strategies as st

from generate_tpch import BASE_COUNTS, ENTITIES, TASK_ARGUMENTS, WIDGET_LIST, check_arguments, check_count, expected_count, generate_tpch, parse_scale_factor

from notebooks.common.cli import parse_task_args

HYPOTHESIS_SEED = int(os.environ.get("HYPOTHESIS_SEED", "0"))
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
# Row counts DuckDB 1.5.6 generated at scale factor 0.01 (checked in the Spark runtime image).
COUNTS_AT_0_01 = {"region": 5, "nation": 25, "supplier": 100, "customer": 1500, "part": 2000, "partsupp": 8000, "orders": 15000, "lineitem": 60175}


def test_task_arguments_need_an_entity_and_default_to_scale_factor_0_01():
    assert check_arguments(parse_task_args(TASK_ARGUMENTS, ["--entity", "orders"])) == ("orders", Decimal("0.01"))
    assert check_arguments(parse_task_args(TASK_ARGUMENTS, ["--entity", "lineitem", "--scale-factor", "0.1"])) == ("lineitem", Decimal("0.1"))
    with pytest.raises(SystemExit) as error:
        parse_task_args(TASK_ARGUMENTS, [])
    assert error.value.code == 2
    for args in (["--entity", "lineitems"], ["--entity", "orders", "--scale-factor", "2"]):
        with pytest.raises(ValueError):  # the notebook's own checks; the common parser doesn't check values
            check_arguments(parse_task_args(TASK_ARGUMENTS, args))
    assert WIDGET_LIST == list(TASK_ARGUMENTS)


@pytest.mark.parametrize("text", ["0", "-0.01", "1.001", "0.0005", "0.0101", "abc", "NaN", "Infinity", ""])
def test_scale_factors_outside_the_rule_are_refused(text):
    with pytest.raises(ValueError, match="from 0.001 to 1"):
        parse_scale_factor(text)


def test_the_counts_duckdb_generated_meet_the_rules():
    for entity, count in COUNTS_AT_0_01.items():
        check_count(entity, Decimal("0.01"), count, COUNTS_AT_0_01["orders"])
    with pytest.raises(RuntimeError, match="TPC-H supplier at scale factor 0.01: 99 rows, expected 100"):
        check_count("supplier", Decimal("0.01"), 99)
    with pytest.raises(RuntimeError, match="expected 15000 to 105000"):
        check_count("lineitem", Decimal("0.01"), 14999, 15000)
    with pytest.raises(ValueError, match="unknown TPC-H entity"):
        expected_count("lineitems", Decimal("0.01"))


def test_the_workflow_runs_every_entity_as_its_own_task():
    workflow = json.loads((REPOSITORY_ROOT / "workflows/sample/generate_tpch.json").read_text(encoding="utf-8"))
    assert [task["name"] for task in workflow["tasks"]] == [f"generate_{entity}" for entity in ENTITIES]
    assert all(task["entrypoint"] == "other/generate_tpch.py" and task["args"] == ["--entity", task["name"].removeprefix("generate_")] for task in workflow["tasks"])
    assert all("runs_after" not in task for task in workflow["tasks"])


# --- Properties ----------------------------------------------------------------------

thousandths = st.integers(min_value=1, max_value=1000)


@seed(HYPOTHESIS_SEED)
@settings(max_examples=200, print_blob=True)
@given(thousandths, st.sampled_from(sorted(BASE_COUNTS)))
def test_p6_scaled_counts_equal_integer_arithmetic_on_thousandths(steps, entity):
    scale_factor = parse_scale_factor(f"{steps / 1000:.3f}")
    assert expected_count(entity, scale_factor) == (BASE_COUNTS[entity] * steps // 1000,) * 2
    assert BASE_COUNTS[entity] * steps % 1000 == 0  # every allowed scale gives a whole count


@seed(HYPOTHESIS_SEED)
@settings(max_examples=200, print_blob=True)
@given(st.decimals(allow_nan=True, allow_infinity=True))
def test_p7_exactly_the_documented_scale_factors_are_accepted(value):
    text = str(value)
    valid = value.is_finite() and Decimal("0.001") <= value <= 1 and value == value.quantize(Decimal("0.001"))
    if valid:
        assert parse_scale_factor(text) == value
    else:
        with pytest.raises(ValueError):
            parse_scale_factor(text)


# --- DuckDB (only where the requirements.txt extras are installed) ---------------------


def test_duckdb_generates_and_checks_every_entity():
    pytest.importorskip("duckdb")
    for entity in ENTITIES:
        assert generate_tpch(entity, Decimal("0.001")) > 0

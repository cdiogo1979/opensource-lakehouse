"""The tpch bronze notebook's rules (tpch R1, R2, R5 to R8, R18; P1, P3). Spark is not needed; DuckDB tests skip without it."""

import json
import os
import re
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from hypothesis import given, seed, settings, strategies as st

import bronze_ingestion as bronze
from notebooks.common.cli import parse_task_args

HYPOTHESIS_SEED = int(os.environ.get("HYPOTHESIS_SEED", "0"))
CONFIG = {"storage_path": "s3a://bucket-default-dev/", "catalog_name": "lakehouse_dev", "database_name": "default_lhdev"}


def test_task_arguments_need_an_entity_and_default_to_scale_factor_0_01():
    assert bronze.check_arguments(parse_task_args(bronze.TASK_ARGUMENTS, ["--entity", "orders"])) == ("orders", Decimal("0.01"))
    assert bronze.WIDGET_LIST == ["entity", "scale_factor"]
    for arguments in ({"entity": "lineitems", "scale_factor": "0.01"}, {"entity": "orders", "scale_factor": "2"}):
        with pytest.raises(ValueError):
            bronze.check_arguments(arguments)


def test_names_and_locations_follow_the_conventions():
    assert bronze.bronze_table_name("region") == "tpch_region_db_brz"
    assert bronze.qualified_table(CONFIG, "tpch_region_db_brz") == "lakehouse_dev.default_lhdev.tpch_region_db_brz"
    assert bronze.table_location(CONFIG, "tpch_region_db_brz") == "s3a://bucket-default-dev/lakehouse_dev/default_lhdev/tpch_region_db_brz"
    with pytest.raises(ValueError, match="unknown TPC-H entity"):
        bronze.bronze_table_name("Region")


def test_the_type_map_keeps_duckdb_types_exactly():
    assert [bronze.spark_type(t) for t in ("INTEGER", "BIGINT", "DECIMAL(15,2)", "DATE", "VARCHAR")] == ["int", "bigint", "decimal(15,2)", "date", "string"]
    for unsupported in ("DOUBLE", "TIMESTAMP", "decimal(15,2)", "DECIMAL(15, 2)", ""):
        with pytest.raises(ValueError, match="unsupported DuckDB column type"):
            bronze.spark_type(unsupported)


def test_decimals_and_dates_leave_duckdb_as_text():
    columns = [("o_orderkey", "BIGINT"), ("o_totalprice", "DECIMAL(15,2)"), ("o_orderdate", "DATE"), ("o_comment", "VARCHAR")]
    assert bronze.select_sql("orders", columns) == ("SELECT o_orderkey, CAST(o_totalprice AS VARCHAR) AS o_totalprice, CAST(o_orderdate AS VARCHAR) AS o_orderdate, o_comment FROM orders")
    with pytest.raises(ValueError):
        bronze.select_sql("orders; DROP", columns)


def test_the_targets_and_summary_name_the_environment_bucket_table_and_location():
    started = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
    expected_targets = {
        "environment": None,
        "bucket": "bucket-default-dev",
        "catalog": "lakehouse_dev",
        "database": "default_lhdev",
        "table": "lakehouse_dev.default_lhdev.tpch_region_db_brz",
        "location": "s3a://bucket-default-dev/lakehouse_dev/default_lhdev/tpch_region_db_brz",
    }
    assert bronze.targets(CONFIG, "region") == expected_targets
    record = bronze.summary(CONFIG, "region", Decimal("0.01"), started, {"rows_appended": 5, "created": True})
    assert json.loads(json.dumps(record)) == {
        "layer": "bronze",
        "entity": "region",
        "scale_factor": "0.01",
        "bronze_ingestion_timestamp": "2026-11-11T12:00:00+00:00",
        **expected_targets,
        "rows_appended": 5,
        "created": True,
    }


def test_generation_runs_no_count_query():
    source = (bronze.generate_entity.__code__.co_consts, bronze.generate_entity.__doc__)
    assert "count(" not in repr(source)
    assert not hasattr(bronze, "check_count") and not hasattr(bronze, "expected_count")


def test_duckdb_generates_every_entity_with_mapped_types():
    pytest.importorskip("duckdb")
    pytest.importorskip("pandas")
    for entity in bronze.ENTITIES:
        columns, frame = bronze.generate_entity(entity, Decimal("0.001"))
        assert len(frame) > 0 and [name for name, _ in columns] == list(frame.columns)
        for name, duckdb_type in columns:
            bronze.spark_type(duckdb_type)
            if duckdb_type.startswith(bronze.TEXT_TYPES):
                assert all(isinstance(value, str) for value in frame[name].head(5))


# --- Properties ----------------------------------------------------------------------

names = st.from_regex(r"\A[a-z][a-z0-9_]{0,15}\Z")
buckets = st.from_regex(r"\A[a-z0-9][a-z0-9-]{1,20}[a-z0-9]\Z")


@seed(HYPOTHESIS_SEED)
@settings(max_examples=200, print_blob=True)
@given(buckets, st.sampled_from(["s3a", "s3"]), st.sampled_from(["", "/", "/root", "/root/"]), names, names, st.sampled_from(bronze.ENTITIES))
def test_p1_locations_join_four_parts_with_one_slash_and_names_round_trip(bucket, scheme, prefix, catalog, database, entity):
    config = {"storage_path": f"{scheme}://{bucket}{prefix}", "catalog_name": catalog, "database_name": database}
    table = bronze.bronze_table_name(entity)
    location = bronze.table_location(config, table)
    assert location == f"{scheme}://{bucket}{prefix.rstrip('/')}/{catalog}/{database}/{table}"
    assert "//" not in location.split("://", 1)[1]
    assert bronze.qualified_table(config, table).split(".") == [catalog, database, table]


duckdb_types = st.one_of(
    st.sampled_from(sorted(bronze.SIMPLE_TYPES)),
    st.builds(lambda p, s: f"DECIMAL({p},{s})", st.integers(1, 38), st.integers(0, 10)),
    st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ(),0123456789 ", max_size=14),
)


@seed(HYPOTHESIS_SEED)
@settings(max_examples=300, print_blob=True)
@given(duckdb_types)
def test_p3_the_type_map_gives_the_documented_type_or_refuses(duckdb_type):
    decimal = re.fullmatch(r"DECIMAL\((\d+),(\d+)\)", duckdb_type)
    if decimal:
        assert bronze.spark_type(duckdb_type) == f"decimal({decimal.group(1)},{decimal.group(2)})"
    elif duckdb_type in bronze.SIMPLE_TYPES:
        assert bronze.spark_type(duckdb_type) == bronze.SIMPLE_TYPES[duckdb_type]
    else:
        with pytest.raises(ValueError):
            bronze.spark_type(duckdb_type)

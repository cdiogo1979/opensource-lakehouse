"""The tpch silver notebook's rules (tpch R1, R3, R11, R12, R14 to R16, R18; P2, P4, P5, P6). Spark is faked or not needed."""

import os
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from hypothesis import given, seed, settings, strategies as st

import silver_processing as silver
from notebooks.common.cli import option_name, parse_task_args

HYPOTHESIS_SEED = int(os.environ.get("HYPOTHESIS_SEED", "0"))
CONFIG = {
    "storage_path": "s3a://bucket-default-dev/",
    "catalog_name": "lakehouse_dev",
    "database_name": "default_lhdev",
    "checkpoint_path": "s3ckpt://bucket-default-dev/checkpoints",
}


def test_task_arguments_need_an_entity_and_default_to_no_lookback():
    assert silver.check_arguments(parse_task_args(silver.TASK_ARGS_DEFINITION, ["--entity", "lineitem"])) == ("lineitem", 0)
    assert silver.check_arguments(parse_task_args(silver.TASK_ARGS_DEFINITION, ["--entity", "region", "--silver-lookback-days", "7"])) == ("region", 7)
    example = [f"{option_name(name)}={value}" for name, value in silver.TASK_ARGS_VALUES.items()]
    assert silver.check_arguments(parse_task_args(silver.TASK_ARGS_DEFINITION, example))  # the Jupyter example is valid
    for text in ("-1", "1.5", " 7", "07", "3651", "", "seven"):
        with pytest.raises(ValueError, match="silver_lookback_days"):
            silver.parse_lookback_days(text)


def test_merge_keys_cover_the_eight_entities():
    assert silver.MERGE_KEYS["partsupp"] == ("ps_partkey", "ps_suppkey") and silver.MERGE_KEYS["lineitem"] == ("l_orderkey", "l_linenumber")
    assert sorted(silver.MERGE_KEYS) == sorted(("region", "nation", "supplier", "customer", "part", "partsupp", "orders", "lineitem"))


def test_names_locations_and_the_checkpoint_follow_the_conventions():
    assert silver.silver_table_name("region") == "tpch_region" and silver.bronze_table_name("region") == "tpch_region_db_brz"
    assert silver.table_location(CONFIG, "tpch_region") == "s3a://bucket-default-dev/lakehouse_dev/default_lhdev/tpch_region"
    assert silver.checkpoint_location(CONFIG, "tpch_region") == "s3ckpt://bucket-default-dev/checkpoints/tpch/tpch_region"
    for base in (None, "", "s3a://bucket-default-dev/checkpoints", "s3ckpt://", "s3ckpt:///"):
        with pytest.raises(ValueError, match="checkpoint_path"):
            silver.checkpoint_location({**CONFIG, "checkpoint_path": base}, "tpch_region")


def test_the_targets_name_source_target_locations_bucket_and_checkpoint():
    assert silver.targets(CONFIG, "region") == {
        "environment": None,
        "bucket": "bucket-default-dev",
        "catalog": "lakehouse_dev",
        "database": "default_lhdev",
        "source": "lakehouse_dev.default_lhdev.tpch_region_db_brz",
        "source_location": "s3a://bucket-default-dev/lakehouse_dev/default_lhdev/tpch_region_db_brz",
        "table": "lakehouse_dev.default_lhdev.tpch_region",
        "location": "s3a://bucket-default-dev/lakehouse_dev/default_lhdev/tpch_region",
        "checkpoint": "s3ckpt://bucket-default-dev/checkpoints/tpch/tpch_region",
        "checkpoint_bucket": "bucket-default-dev",
    }


def test_the_merge_updates_only_with_newer_rows():
    assert silver.merge_sql("c.d.tpch_lineitem", "v", silver.MERGE_KEYS["lineitem"]) == (
        "MERGE INTO c.d.tpch_lineitem t USING v s ON t.l_orderkey = s.l_orderkey AND t.l_linenumber = s.l_linenumber "
        "WHEN MATCHED AND s.bronze_ingestion_timestamp > t.bronze_ingestion_timestamp THEN UPDATE SET * "
        "WHEN NOT MATCHED THEN INSERT *"
    )


def test_the_lookback_starts_n_days_before_the_run():
    now = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
    assert silver.start_timestamp_ms(0, now) == int(now.timestamp() * 1000)
    assert silver.start_timestamp_ms(2, now) == int(now.timestamp() * 1000) - 2 * 86_400_000


class FakeFileSystem:
    def __init__(self, existing):
        self.existing, self.deleted = set(existing), []

    def exists(self, path):
        return path.text in self.existing

    def delete(self, path, recursive):
        self.deleted.append((path.text, recursive))
        self.existing.discard(path.text)
        return True


def fake_spark(filesystem):
    class Path:
        def __init__(self, text):
            self.text = text

        def getFileSystem(self, configuration):
            return filesystem

    hadoop = SimpleNamespace(fs=SimpleNamespace(Path=Path))
    return SimpleNamespace(_jvm=SimpleNamespace(org=SimpleNamespace(apache=SimpleNamespace(hadoop=hadoop))), _jsc=SimpleNamespace(hadoopConfiguration=lambda: None))


def test_a_reset_deletes_exactly_the_entity_checkpoint():
    location = "s3ckpt://bucket-default-dev/checkpoints/tpch/tpch_orders"
    filesystem = FakeFileSystem({location, "s3ckpt://bucket-default-dev/checkpoints/tpch/tpch_region"})
    assert silver.reset_checkpoint(fake_spark(filesystem), CONFIG, "orders") is True
    assert filesystem.deleted == [(location, True)]
    assert silver.reset_checkpoint(fake_spark(filesystem), CONFIG, "orders") is False  # an absent checkpoint is not an error
    with pytest.raises(ValueError):
        silver.reset_checkpoint(fake_spark(filesystem), CONFIG, "../tpch_region")


# --- Properties ----------------------------------------------------------------------

buckets = st.from_regex(r"\A[a-z0-9][a-z0-9-]{1,20}[a-z0-9]\Z")


@seed(HYPOTHESIS_SEED)
@settings(max_examples=200, print_blob=True)
@given(buckets, st.sampled_from(["", "/"]), st.sampled_from(sorted(silver.MERGE_KEYS)), st.sampled_from(["s3a://", "s3://", "file:/", "s3ckpt:"]))
def test_p2_checkpoints_sit_under_checkpoint_path_and_need_s3ckpt(bucket, slash, entity, other_scheme):
    base = f"s3ckpt://{bucket}/checkpoints{slash}"
    location = silver.checkpoint_location({**CONFIG, "checkpoint_path": base}, silver.silver_table_name(entity))
    assert location.startswith(base.rstrip("/") + "/") and location.endswith(f"/tpch/tpch_{entity}")
    with pytest.raises(ValueError):
        silver.checkpoint_location({**CONFIG, "checkpoint_path": f"{other_scheme}{bucket}/checkpoints"}, "tpch_region")


@seed(HYPOTHESIS_SEED)
@settings(max_examples=300, print_blob=True)
@given(st.one_of(st.integers(-5, 4000).map(str), st.text(max_size=6)))
def test_p4_exactly_0_to_3650_in_digits_is_accepted_and_round_trips(text):
    accepted = text.isascii() and text.isdigit() and (text == "0" or not text.startswith("0")) and int(text) <= 3650
    if accepted:
        assert str(silver.parse_lookback_days(text)) == text
    else:
        with pytest.raises(ValueError):
            silver.parse_lookback_days(text)


@seed(HYPOTHESIS_SEED)
@settings(max_examples=100, print_blob=True)
@given(st.lists(st.from_regex(r"\A[a-z][a-z0-9_]{0,10}\Z"), min_size=1, max_size=4, unique=True))
def test_p5_the_merge_condition_names_every_key_once_in_order(keys):
    parts = silver.merge_condition(tuple(keys)).split(" AND ")
    assert parts == [f"t.{key} = s.{key}" for key in keys]


def reference_merge(silver_rows, batch):
    """R11 and R12 on plain rows: newest row per key in the batch, applied only when strictly newer."""
    latest = {}
    for key, timestamp, value in batch:
        if key not in latest or timestamp > latest[key][0]:
            latest[key] = (timestamp, value)
    merged = dict(silver_rows)
    for key, (timestamp, value) in latest.items():
        if key not in merged or timestamp > merged[key][0]:
            merged[key] = (timestamp, value)
    return merged


# Bronze runs: each run has one timestamp (its index) and unique keys, as in the notebook.
bronze_runs = st.lists(st.dictionaries(st.integers(0, 6), st.integers(0, 99), min_size=1, max_size=5), min_size=1, max_size=6)


@seed(HYPOTHESIS_SEED)
@settings(max_examples=300, print_blob=True)
@given(bronze_runs, st.data())
def test_p6_any_batch_grouping_gives_the_newest_row_per_key_and_replays_change_nothing(runs, data):
    rows = [(key, run, value) for run, keys in enumerate(runs) for key, value in keys.items()]
    newest = {}
    for key, run, value in rows:
        newest[key] = (run, value)  # later runs come later in rows
    cuts = sorted(data.draw(st.sets(st.integers(1, max(len(rows) - 1, 1)), max_size=len(rows))))
    batches = [rows[start:end] for start, end in zip([0, *cuts], [*cuts, len(rows)]) if rows[start:end]]
    merged = {}
    for batch in batches:
        merged = reference_merge(merged, batch)
    assert merged == newest
    replay = data.draw(st.lists(st.sampled_from(rows), max_size=len(rows)))
    assert reference_merge(merged, replay) == merged

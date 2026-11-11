"""The tpch_medallion workflow (tpch R19): two lanes, bronze then silver per entity."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENTITIES = ("region", "nation", "supplier", "customer", "part", "partsupp", "orders", "lineitem")


def load_tasks():
    workflow = json.loads((ROOT / "workflows/tpch/tpch_medallion.json").read_text())
    assert workflow["name"] == "tpch_medallion" and workflow["schedule"] is None
    return {task["name"]: task for task in workflow["tasks"]}


def test_every_entity_has_a_bronze_then_a_silver_task_and_no_lookback():
    tasks = load_tasks()
    assert len(tasks) == 16
    for entity in ENTITIES:
        bronze, silver = tasks[f"tpch_{entity}_db_brz_load"], tasks[f"tpch_{entity}_load"]
        assert bronze["entrypoint"] == "bronze/bronze_ingestion.py" and bronze["args"] == ["--entity", entity]
        assert silver["entrypoint"] == "silver/silver_processing.py" and silver["args"] == ["--entity", entity]
        assert f"tpch_{entity}_db_brz_load" in silver["runs_after"]
    for task in tasks.values():
        assert (ROOT / "notebooks/workload/tpch" / task["entrypoint"]).is_file()
        assert task["retries"] == 1 and task["retry_delay_seconds"] == 60


def test_two_lanes_keep_at_most_one_bronze_and_one_silver_job_running():
    tasks = load_tasks()
    for index, entity in enumerate(ENTITIES):
        bronze, silver = tasks[f"tpch_{entity}_db_brz_load"], tasks[f"tpch_{entity}_load"]
        previous = ENTITIES[index - 1] if index else None
        assert bronze.get("runs_after", []) == ([f"tpch_{previous}_db_brz_load"] if previous else [])
        assert silver["runs_after"] == [f"tpch_{entity}_db_brz_load"] + ([f"tpch_{previous}_load"] if previous else [])

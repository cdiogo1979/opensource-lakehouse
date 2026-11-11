"""The tpch_medallion workflow (tpch R19)."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENTITIES = ("region", "nation", "supplier", "customer", "part", "partsupp", "orders", "lineitem")


def test_every_entity_has_a_bronze_then_a_silver_task_and_no_lookback():
    workflow = json.loads((ROOT / "workflows/tpch/tpch_medallion.json").read_text())
    assert workflow["name"] == "tpch_medallion" and workflow["schedule"] is None
    tasks = {task["name"]: task for task in workflow["tasks"]}
    assert len(tasks) == 16
    for entity in ENTITIES:
        bronze, silver = tasks[f"tpch_{entity}_db_brz_load"], tasks[f"tpch_{entity}_load"]
        assert bronze["entrypoint"] == "bronze/bronze_ingestion.py" and bronze["args"] == ["--entity", entity] and "runs_after" not in bronze
        assert silver["entrypoint"] == "silver/silver_processing.py" and silver["args"] == ["--entity", entity]
        assert silver["runs_after"] == [f"tpch_{entity}_db_brz_load"]
    for task in tasks.values():
        assert (ROOT / "notebooks/workload/tpch" / task["entrypoint"]).is_file()

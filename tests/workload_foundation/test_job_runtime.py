"""start_spark_job: this repository's config, then the platform's lakehouse_spark (BR-J1 to BR-J5; P7)."""

import sys
import types
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from notebooks.common import job_runtime

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def platform(monkeypatch):
    """A fake lakehouse_spark that records how the session was requested."""
    calls = []
    module = types.ModuleType("lakehouse_spark")
    module.create_spark_session = lambda app_name, catalog: calls.append((app_name, catalog)) or "spark"
    monkeypatch.setitem(sys.modules, "lakehouse_spark", module)
    monkeypatch.delenv("LAKEHOUSE_PRODUCT", raising=False)
    monkeypatch.delenv("LAKEHOUSE_ENVIRONMENT", raising=False)
    return calls


def write_config(directory: Path, name: str, **extra):
    directory.mkdir(parents=True, exist_ok=True)
    lines = ["storage_path: s3a://bucket-default-uat/", "database_name: default_lhuat", "catalog_name: lakehouse_uat"]
    lines += [f"{key}: {value}" for key, value in extra.items()]
    (directory / name).write_text("\n".join(lines) + "\n")


def test_airflow_passes_the_config_through_and_hands_only_the_catalog_to_the_platform(platform, tmp_path, monkeypatch):
    write_config(tmp_path, "uat.yml", source_dataset="raw.orders_uat")
    write_config(tmp_path / "sales", "uat.yml", source_dataset="raw.sales_uat")
    spark, config = job_runtime.start_spark_job("load", ["--environment", "uat", "--config-dir", str(tmp_path)])
    assert spark == "spark" and platform == [("uat-load", "lakehouse_uat")]
    assert config["source_dataset"] == "raw.orders_uat"
    monkeypatch.setenv("LAKEHOUSE_PRODUCT", "sales")
    _, config = job_runtime.start_spark_job("load", ["--environment", "uat", "--config-dir", str(tmp_path)])
    assert config["source_dataset"] == "raw.sales_uat"  # the product folder, as the platform selects it


def test_jupyter_uses_dev_or_the_chosen_environment_and_ignores_the_product(platform, monkeypatch):
    monkeypatch.setitem(sys.modules, "ipykernel", types.ModuleType("ipykernel"))
    monkeypatch.setenv("LAKEHOUSE_PRODUCT", "sales")
    _, config = job_runtime.start_spark_job("generate_tpch")
    assert config.environment == "dev" and platform[-1] == ("dev-generate_tpch", "lakehouse_dev")
    monkeypatch.setenv("LAKEHOUSE_ENVIRONMENT", "uat")
    _, config = job_runtime.start_spark_job("generate_tpch")
    assert config.environment == "uat" and platform[-1] == ("uat-generate_tpch", "lakehouse_uat")


def test_a_config_without_catalog_name_is_refused(platform, tmp_path):
    (tmp_path / "uat.yml").write_text("storage_path: s3a://b/\ndatabase_name: d\n")
    with pytest.raises(ValueError, match="no catalog_name"):
        job_runtime.start_spark_job("load", ["--environment", "uat", "--config-dir", str(tmp_path)])
    assert platform == []


def test_the_repository_holds_no_platform_session_settings():
    source = (REPOSITORY_ROOT / "notebooks/common/job_runtime.py").read_text()
    for platform_detail in (
        "polaris:8181",
        "spark.sql.catalog",
        "LakehouseTokenAuthManager",
        "redaction.regex",
        "LAKEHOUSE_TOKEN_",
        "spark-files",
        "LAKEHOUSE_CONFIG_DIR",
        "LAKEHOUSE_BUNDLE_CONFIG_DIR",
    ):
        assert platform_detail not in source


@settings(max_examples=200, print_blob=True)
@given(st.one_of(st.none(), st.sampled_from(["dev", "uat", "prod", "", "DEV", "staging", "prod "]), st.text(max_size=8)))
def test_p7_only_dev_uat_and_prod_are_jupyter_environments(value):
    environ = {} if value is None else {"LAKEHOUSE_ENVIRONMENT": value}
    if value in (None, ""):
        assert job_runtime.jupyter_environment(environ) == "dev"
    elif value in ("dev", "uat", "prod"):
        assert job_runtime.jupyter_environment(environ) == value
    else:
        with pytest.raises(ValueError):
            job_runtime.jupyter_environment(environ)

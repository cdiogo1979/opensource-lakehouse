"""Example-based checks for the environment initialization workload."""

import pytest

import init_environment
from config_loader import EnvironmentConfig, load_environment_config
from init_environment import (
    SAMPLE_ROWS,
    SAMPLE_SCHEMA,
    SAMPLE_TABLE_NAME,
    create_namespace,
    write_sample_dataset,
)
from dag_defaults import identity_for_bundle, standard_dag_kwargs


class _FakeDataFrameWriter:
    """Capture the table write contract without starting Spark."""

    def __init__(self):
        self.write_mode = None
        self.options = {}
        self.table_name = None

    def mode(self, write_mode):
        self.write_mode = write_mode
        return self

    def option(self, key, value):
        self.options[key] = value
        return self

    def saveAsTable(self, table_name):
        self.table_name = table_name
        self.spark.tables.add(table_name)


class _FakeCatalog:
    """Model the catalog existence checks used by the workload."""

    def __init__(self, namespaces, tables):
        self.namespaces = namespaces
        self.tables = tables

    def databaseExists(self, database_name):
        return database_name in self.namespaces

    def tableExists(self, table_identifier):
        return table_identifier in self.tables


class _FakeSpark:
    """Record catalog and DataFrame operations used by the job."""

    def __init__(self):
        self.statements = []
        self.namespaces = set()
        self.tables = set()
        self.catalog = _FakeCatalog(self.namespaces, self.tables)
        self.writer = _FakeDataFrameWriter()
        self.writer.spark = self

    def sql(self, statement):
        self.statements.append(statement)

    def createDataFrame(self, rows, schema):
        assert rows == SAMPLE_ROWS
        assert schema == SAMPLE_SCHEMA
        return type("FakeDataFrame", (), {"write": self.writer})()


def test_config_loader_exposes_arbitrary_nested_settings(tmp_path):
    """Applications can use new nested settings without loader changes."""
    (tmp_path / "dev.yml").write_text(
        "storage_path: s3a://bucket-dev/root/\n" "database_name: dev_db\n" "spark:\n" "  executor:\n" "    memory: 4g\n" "    instances: 3\n" "  labels: [sample, lakehouse]\n",
        encoding="utf-8",
    )

    config = load_environment_config("dev", tmp_path)

    assert config["spark"]["executor"]["memory"] == "4g"
    assert config.get("spark")["executor"]["instances"] == 3
    assert config["spark"]["labels"] == ("sample", "lakehouse")
    assert config.to_dict()["spark"]["labels"] == ["sample", "lakehouse"]


def test_standard_dag_settings_share_manual_environment_defaults():
    """DAGs receive the same schedule, version, tags, and ID conventions."""
    settings = standard_dag_kwargs(
        environment="uat",
        workload_name="refresh_dimensions",
        description="Refresh the dimensions.",
        schedule=None,
        tags=("spark",),
    )

    assert settings["dag_id"] == "uat-refresh_dimensions"
    assert settings["schedule"] is None
    assert settings["catchup"] is False
    assert settings["tags"] == ["uat", "spark"]
    assert settings["rerun_with_latest_version"] is False
    assert settings["start_date"].isoformat() == "2024-01-01T00:00:00"


@pytest.mark.parametrize(
    ("bundle_name", "expected_identity"),
    [
        ("lakehouse-main", ("main", "prod")),
        ("lakehouse-prod", ("main", "prod")),
        ("lakehouse-uat", ("uat", "uat")),
        ("lakehouse-dev", ("dev", "dev")),
        ("lakehouse-feature-42", ("dev", "dev")),
    ],
)
def test_bundle_name_selects_environment(tmp_path, bundle_name, expected_identity):
    """Stable Airflow bundle names select environment independent of Git ref."""
    dags_dir = tmp_path / "dag_bundles" / bundle_name / "tracking_repo" / "dags"
    dags_dir.mkdir(parents=True)

    assert identity_for_bundle(dags_dir) == expected_identity


def test_versioned_bundle_checkout_selects_environment(tmp_path):
    """Task-version checkout paths also retain the configured bundle name."""
    dags_dir = tmp_path / "dag_bundles" / "lakehouse-main" / "versions" / "abc123" / "dags"
    dags_dir.mkdir(parents=True)

    assert identity_for_bundle(dags_dir) == ("main", "prod")


def test_local_dag_path_defaults_to_dev(tmp_path):
    """A non-versioned local DAG folder uses the development environment."""
    dags_dir = tmp_path / "dags"
    dags_dir.mkdir()

    assert identity_for_bundle(dags_dir) == ("dev", "dev")


def test_create_namespace_uses_idempotent_catalog_statement():
    """The configured namespace is created only through IF NOT EXISTS."""
    config = EnvironmentConfig(
        environment="dev",
        settings={"storage_path": "s3a://bucket-dev/root/", "database_name": "dev_db"},
    )
    spark = _FakeSpark()

    create_namespace(spark, config)

    assert spark.statements == ["CREATE NAMESPACE IF NOT EXISTS dev_db"]


def test_smoke_write_is_limited_to_dedicated_table_and_child_path():
    """The retained smoke test overwrites only its dedicated table path."""
    config = EnvironmentConfig(
        environment="dev",
        settings={"storage_path": "s3a://bucket-dev/root/", "database_name": "dev_db"},
    )
    spark = _FakeSpark()

    write_sample_dataset(spark, config)

    assert SAMPLE_TABLE_NAME == "sample_spark_job_output"
    assert spark.writer.write_mode == "overwrite"
    assert spark.writer.options == {"path": "s3a://bucket-dev/root/sample_spark_job_output"}
    assert spark.writer.table_name == "dev_db.sample_spark_job_output"


def test_initialization_creates_namespace_then_writes_smoke_table():
    """Catalog setup and the table write initialize the object storage prefix."""
    config = EnvironmentConfig(
        environment="dev",
        settings={"storage_path": "s3a://bucket-dev/root/", "database_name": "dev_db"},
    )
    spark = _FakeSpark()

    init_environment.initialize_environment(spark, config)

    assert spark.statements == ["CREATE NAMESPACE IF NOT EXISTS dev_db"]
    assert spark.writer.table_name == "dev_db.sample_spark_job_output"
    assert spark.writer.options["path"] == ("s3a://bucket-dev/root/sample_spark_job_output")

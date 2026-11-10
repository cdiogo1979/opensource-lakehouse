"""Example-based checks for the environment initialization workload."""

from config_loader import EnvironmentConfig, load_environment_config
from test_environment import (
    SAMPLE_ROWS,
    SAMPLE_SCHEMA,
    SAMPLE_TABLE_NAME,
    write_sample_dataset,
)


class _FakeDataFrameWriter:
    """Capture the table write contract without starting Spark."""

    def __init__(self):
        self.source_format = None
        self.write_mode = None
        self.options = {}
        self.table_name = None

    def format(self, source_format):
        self.source_format = source_format
        return self

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
        self.tables = set()
        self.catalog = _FakeCatalog(set(), self.tables)
        self.writer = _FakeDataFrameWriter()
        self.writer.spark = self

    def createDataFrame(self, rows, schema):
        assert rows == SAMPLE_ROWS
        assert schema == SAMPLE_SCHEMA
        return type(
            "FakeDataFrame",
            (),
            {
                "write": self.writer,
                "withColumn": lambda dataframe, name, expression: dataframe,
            },
        )()


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


def test_smoke_write_is_limited_to_dedicated_table_and_child_path():
    """The retained smoke test overwrites only its dedicated table path."""
    config = EnvironmentConfig(
        environment="dev",
        settings={"storage_path": "s3a://bucket-dev/root/", "catalog_name": "lakehouse", "database_name": "dev_db"},
    )
    spark = _FakeSpark()

    write_sample_dataset(spark, config)

    assert SAMPLE_TABLE_NAME == "sample_spark_job_output"
    assert spark.writer.source_format == "iceberg"
    assert spark.writer.write_mode == "overwrite"
    assert spark.writer.options == {"path": "s3a://bucket-dev/root/lakehouse/dev_db/sample_spark_job_output"}
    assert spark.writer.table_name == "dev_db.sample_spark_job_output"

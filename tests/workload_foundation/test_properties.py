"""Hypothesis properties for configuration and environment initialization."""

import os
import string
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, seed, settings, strategies as st
import yaml

from config_loader import EnvironmentConfig, load_environment_config
from init_environment import initialize_environment

HYPOTHESIS_SEED = int(os.environ.get("HYPOTHESIS_SEED", "0"))
ENVIRONMENTS = ("dev", "uat", "prod")
TOKEN_CHARS = string.ascii_lowercase + string.digits


@st.composite
def environment_config_strategy(draw):
    """Generate realistic non-secret EnvironmentConfig values."""
    environment = draw(st.sampled_from(ENVIRONMENTS))
    bucket_token = draw(st.text(alphabet=TOKEN_CHARS, min_size=1, max_size=16))
    prefix_tokens = draw(st.lists(st.text(alphabet=TOKEN_CHARS, min_size=1, max_size=12), max_size=4))
    database_token = draw(st.text(alphabet=TOKEN_CHARS + "_", min_size=1, max_size=24))
    suffix = "/".join(prefix_tokens)
    storage_path = f"s3a://bucket-{bucket_token}/{environment}/"
    if suffix:
        storage_path = f"{storage_path}{suffix}/"
    return EnvironmentConfig(
        environment=environment,
        settings={
            "storage_path": storage_path,
            "database_name": f"{environment}_{database_token}",
        },
    )


@seed(HYPOTHESIS_SEED)
@settings(max_examples=60, print_blob=True)
@given(
    environment=st.sampled_from(ENVIRONMENTS),
    token=st.text(alphabet=TOKEN_CHARS, min_size=1, max_size=24),
)
def test_loader_isolates_environment_files(environment, token):
    """Loading any supported environment returns only that file's values."""
    with TemporaryDirectory() as directory:
        config_dir = Path(directory)
        for selected in ENVIRONMENTS:
            values = {
                "storage_path": f"s3a://bucket-{selected}/{token}/{selected}",
                "database_name": f"{selected}_{token}",
            }
            (config_dir / f"{selected}.yml").write_text(yaml.safe_dump(values), encoding="utf-8")

        config = load_environment_config(environment, config_dir)

        assert config.environment == environment
        assert config["storage_path"] == f"s3a://bucket-{environment}/{token}/{environment}"
        assert config["database_name"] == f"{environment}_{token}"


@seed(HYPOTHESIS_SEED)
@settings(max_examples=60, print_blob=True)
@given(config=environment_config_strategy())
def test_valid_config_values_are_preserved(config):
    """For generated valid values, the loader preserves required config data."""
    values = {
        "storage_path": config["storage_path"],
        "database_name": config["database_name"],
    }
    with TemporaryDirectory() as directory:
        config_dir = Path(directory)
        (config_dir / f"{config.environment}.yml").write_text(yaml.safe_dump(values), encoding="utf-8")

        loaded = load_environment_config(config.environment, config_dir)

        assert loaded == config


YAML_SCALAR = st.one_of(st.none(), st.booleans(), st.integers(min_value=-1000, max_value=1000), st.text(max_size=12))
YAML_VALUE = st.recursive(
    YAML_SCALAR,
    lambda children: st.lists(children, max_size=4) | st.dictionaries(st.text(max_size=12), children, max_size=4),
    max_leaves=10,
)


@seed(HYPOTHESIS_SEED)
@settings(max_examples=60, print_blob=True)
@given(extra_value=YAML_VALUE)
def test_arbitrary_nested_yaml_settings_are_preserved(extra_value):
    """Generic nested keys and YAML values remain available to applications."""
    values = {
        "storage_path": "s3a://bucket-dev/root",
        "database_name": "dev_db",
        "application_options": {"custom_value": extra_value},
    }
    with TemporaryDirectory() as directory:
        config_dir = Path(directory)
        (config_dir / "dev.yml").write_text(yaml.safe_dump(values), encoding="utf-8")

        config = load_environment_config("dev", config_dir)

        assert config.to_dict()["application_options"]["custom_value"] == extra_value
        assert config.to_dict() == values


@seed(HYPOTHESIS_SEED)
@settings(max_examples=60, print_blob=True)
@given(
    environment=st.sampled_from(ENVIRONMENTS),
    invalid_value=st.one_of(
        st.none(),
        st.integers(),
        st.booleans(),
        st.sampled_from(("", " ", "\t", "\n")),
    ),
    key=st.sampled_from(("storage_path", "database_name")),
)
def test_invalid_required_values_always_fail(environment, invalid_value, key):
    """Generated empty and non-string required values are rejected."""
    values = {
        "storage_path": f"s3a://bucket-{environment}/root",
        "database_name": f"{environment}_db",
    }
    values[key] = invalid_value
    with TemporaryDirectory() as directory:
        config_dir = Path(directory)
        (config_dir / f"{environment}.yml").write_text(yaml.safe_dump(values), encoding="utf-8")

        try:
            load_environment_config(environment, config_dir)
        except ValueError:
            return
        raise AssertionError(f"Invalid value for {key} was accepted: {invalid_value!r}")


@seed(HYPOTHESIS_SEED)
@settings(max_examples=40, print_blob=True)
@given(
    selected=st.sampled_from(ENVIRONMENTS),
    token=st.text(alphabet=TOKEN_CHARS, min_size=1, max_size=12),
)
def test_missing_selected_file_does_not_fall_back(selected, token):
    """A missing selected file fails even when other environment files exist."""
    with TemporaryDirectory() as directory:
        config_dir = Path(directory)
        for environment in ENVIRONMENTS:
            if environment == selected:
                continue
            (config_dir / f"{environment}.yml").write_text(
                yaml.safe_dump(
                    {
                        "storage_path": f"s3a://bucket-{environment}/{token}",
                        "database_name": f"{environment}_{token}",
                    }
                ),
                encoding="utf-8",
            )

        try:
            load_environment_config(selected, config_dir)
        except FileNotFoundError:
            return
        raise AssertionError(f"Missing {selected}.yml unexpectedly fell back.")


class _FakeDataFrameWriter:
    """Small in-memory model of the Spark write options used by the workload."""

    def __init__(self, spark, rows):
        """Store the fake session and immutable rows for a pending write."""
        self.spark = spark
        self.rows = list(rows)
        self.write_mode = None
        self.options = {}

    def mode(self, write_mode):
        """Set the fake write mode and return this writer for chaining."""
        self.write_mode = write_mode
        return self

    def option(self, key, value):
        """Record a write option and return this writer for chaining."""
        self.options[key] = value
        return self

    def saveAsTable(self, table_name):
        """Apply append or overwrite behavior to the in-memory table model."""
        if self.write_mode == "overwrite":
            self.spark.tables[table_name] = {
                "rows": list(self.rows),
                "path": self.options["path"],
            }
        elif self.write_mode == "append":
            current = self.spark.tables.get(table_name, {"rows": [], "path": None})
            current["rows"].extend(self.rows)
            current["path"] = self.options["path"]
            self.spark.tables[table_name] = current
        else:
            raise AssertionError(f"Unexpected write mode: {self.write_mode!r}")


class _FakeDataFrame:
    """Fake DataFrame exposing the writer interface used by the job."""

    def __init__(self, spark, rows):
        """Create a fake DataFrame backed by the provided Spark model."""
        self.write = _FakeDataFrameWriter(spark, rows)


class _FakeSparkSession:
    """In-memory catalog and table model for the job contract."""

    def __init__(self, initial_rows):
        """Initialize generated catalog, filesystem, and table state."""
        self.tables = {
            "uat_sample_db.sample_spark_job_output": {
                "rows": list(initial_rows),
                "path": "s3a://old-location",
            }
        }
        self.namespaces = {"existing_namespace"}
        self.paths = {"s3a://bucket-uat/unrelated/": "preserve-me"}
        self.operations = []
        self.catalog = self

    def databaseExists(self, database_name):
        """Report whether the in-memory catalog contains a namespace."""
        return database_name in self.namespaces

    def tableExists(self, table_identifier):
        """Report whether the in-memory catalog contains a table."""
        return table_identifier in self.tables

    def sql(self, statement):
        """Model the idempotent namespace creation statement."""
        self.operations.append(("sql", statement))
        prefix = "CREATE NAMESPACE IF NOT EXISTS "
        assert statement.startswith(prefix)
        self.namespaces.add(statement[len(prefix) :])

    def createDataFrame(self, rows, schema):
        """Return a fake DataFrame while accepting the Spark schema argument."""
        del schema
        return _FakeDataFrame(self, rows)


@seed(HYPOTHESIS_SEED)
@settings(max_examples=40, print_blob=True)
@given(
    existing=st.lists(st.tuples(st.text(max_size=12), st.integers()), max_size=20),
)
def test_repeating_initialization_is_idempotent_and_preserves_unrelated_state(existing):
    """Repeated initialization keeps the smoke table and unrelated state stable."""
    config = EnvironmentConfig(
        environment="uat",
        settings={
            "storage_path": "s3a://bucket-uat/sample/",
            "database_name": "uat_sample_db",
        },
    )
    initial_rows = [(f"old-{index}", str(value), int(index)) for index, value in enumerate(existing)]
    once = _FakeSparkSession(initial_rows)
    twice = _FakeSparkSession(initial_rows)
    initialize_environment(once, config)
    initialize_environment(twice, config)
    initialize_environment(twice, config)

    assert once.namespaces == twice.namespaces
    assert "uat_sample_db" in once.namespaces
    assert once.paths == twice.paths
    assert once.tables["uat_sample_db.sample_spark_job_output"]["path"] == "s3a://bucket-uat/sample/sample_spark_job_output"
    assert once.tables == twice.tables
    assert once.paths["s3a://bucket-uat/unrelated/"] == "preserve-me"

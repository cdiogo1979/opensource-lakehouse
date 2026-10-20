"""Example-based validation tests for environment configuration loading."""

import pytest
import yaml

from config_loader import load_environment_config


@pytest.mark.parametrize("environment", ["staging", "../prod", ""])
def test_rejects_unsupported_environment(environment, tmp_path):
    """Unsupported identifiers fail without trying another environment file."""
    with pytest.raises(ValueError, match="Unsupported environment"):
        load_environment_config(environment, tmp_path)


def test_reports_missing_environment_file(tmp_path):
    """A missing selected file raises a contextual file error."""
    with pytest.raises(FileNotFoundError, match="environment 'uat'"):
        load_environment_config("uat", tmp_path)


@pytest.mark.parametrize(
    "contents, message",
    [
        ("storage_path: [\n", "invalid YAML"),
        ("- not-a-mapping\n", "YAML mapping"),
        ("database_name: sample_db\n", "storage_path"),
        ("storage_path: s3a://bucket/root\n", "database_name"),
    ],
)
def test_rejects_malformed_or_incomplete_yaml(contents, message, tmp_path):
    """Malformed YAML and mapping/key omissions fail with useful messages."""
    (tmp_path / "dev.yml").write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_environment_config("dev", tmp_path)


@pytest.mark.parametrize("invalid_value", [None, 0, "", "   "])
@pytest.mark.parametrize("key", ["storage_path", "database_name"])
def test_rejects_empty_or_non_string_required_values(invalid_value, key, tmp_path):
    """Each required value must be a non-blank string."""
    values = {"storage_path": "s3a://bucket/root", "database_name": "sample_db"}
    values[key] = invalid_value
    (tmp_path / "prod.yml").write_text(yaml.safe_dump(values), encoding="utf-8")

    with pytest.raises(ValueError, match=key):
        load_environment_config("prod", tmp_path)


def test_loads_only_the_selected_environment(tmp_path):
    """The selected file populates all values in the immutable config object."""
    (tmp_path / "uat.yml").write_text(
        "storage_path: s3a://uat-bucket/root\ndatabase_name: uat_db\n",
        encoding="utf-8",
    )

    config = load_environment_config("uat", tmp_path)

    assert config.environment == "uat"
    assert config["storage_path"] == "s3a://uat-bucket/root"
    assert config["database_name"] == "uat_db"

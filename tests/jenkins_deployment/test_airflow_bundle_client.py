"""Tests for the dev Git bundle branch-selection client."""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, call

import pytest
from hypothesis import given, strategies as st

import airflow_bundle_client as client
from dags.spark_output import redact_spark_output

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _bundle_config(dev_ref: str = "feature/initial") -> list[dict]:
    """Return a small three-environment Git bundle configuration."""
    return [
        {
            "name": "lakehouse-dev",
            "classpath": "airflow.providers.git.bundles.git.GitDagBundle",
            "kwargs": {"tracking_ref": dev_ref, "git_conn_id": "lakehouse_git"},
        },
        {
            "name": "lakehouse-uat",
            "classpath": "airflow.providers.git.bundles.git.GitDagBundle",
            "kwargs": {"tracking_ref": "uat", "git_conn_id": "lakehouse_git"},
        },
        {
            "name": "lakehouse-prod",
            "classpath": "airflow.providers.git.bundles.git.GitDagBundle",
            "kwargs": {"tracking_ref": "main", "git_conn_id": "lakehouse_git"},
        },
    ]


def _client_settings(config_path: Path) -> dict:
    """Return validated-shape settings for the client API."""
    return {
        "bundle_config_path": config_path,
        "dev_bundle_name": "lakehouse-dev",
        "allowed_branch_prefixes": ["feature/"],
        "apply_timeout_seconds": 30,
        "apply_command": ["apply-bundles", "--config", "{config_path}"],
    }


def _write_config(config_path: Path, bundles: list[dict] | None = None) -> bytes:
    """Write a bundle config and return its original bytes."""
    config_path.write_text(json.dumps(bundles or _bundle_config()), encoding="utf-8")
    return config_path.read_bytes()


def test_show_selected_ref_reads_only_dev_bundle(tmp_path: Path) -> None:
    config_path = tmp_path / "bundles.json"
    _write_config(config_path)

    assert client.show_selected_ref(config_path) == "feature/initial"


def test_select_changes_only_dev_and_invokes_apply_without_shell(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "bundles.json"
    _write_config(config_path)
    completed = subprocess.CompletedProcess(args=["git"], returncode=0)
    mocked_subprocess_run = Mock(return_value=completed)
    monkeypatch.setattr(client.subprocess, "run", mocked_subprocess_run)
    previous_ref, selected_ref = client.select_dev_ref(_client_settings(config_path), "feature/try-new-branch")

    bundles = json.loads(config_path.read_bytes())
    assert (previous_ref, selected_ref) == ("feature/initial", "feature/try-new-branch")
    assert bundles[0]["kwargs"]["tracking_ref"] == "feature/try-new-branch"
    assert bundles[1]["kwargs"]["tracking_ref"] == "uat"
    assert bundles[2]["kwargs"]["tracking_ref"] == "main"
    assert mocked_subprocess_run.call_args_list == [
        call(
            ["git", "check-ref-format", "refs/heads/feature/try-new-branch"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        ),
        call(
            ["apply-bundles", "--config", str(config_path)],
            check=True,
            shell=False,
            capture_output=True,
            text=True,
            timeout=30,
        ),
    ]


@pytest.mark.parametrize("protected_ref", ["dev", "uat", "main"])
def test_protected_ref_is_rejected_before_apply(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, protected_ref: str) -> None:
    config_path = tmp_path / "bundles.json"
    original_bytes = _write_config(config_path)
    mocked_subprocess_run = Mock()
    monkeypatch.setattr(client.subprocess, "run", mocked_subprocess_run)

    with pytest.raises(client.BundleClientError, match="protected ref"):
        client.select_dev_ref(_client_settings(config_path), protected_ref)

    mocked_subprocess_run.assert_not_called()
    assert config_path.read_bytes() == original_bytes


@given(st.sampled_from(["dev", "uat", "main"]))
def test_property_protected_refs_never_pass_validation(protected_ref: str) -> None:
    with pytest.raises(client.BundleClientError, match="protected ref"):
        client.validate_feature_ref(protected_ref)


def test_configured_prefix_policy_is_enforced() -> None:
    with pytest.raises(client.BundleClientError, match="branch prefix"):
        client.validate_feature_ref("bugfix/one", ["feature/"])


def test_invalid_git_branch_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "bundles.json"
    original_bytes = _write_config(config_path)

    def mocked_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=args[0], returncode=1, stderr="invalid")

    monkeypatch.setattr(client.subprocess, "run", mocked_run)

    with pytest.raises(client.BundleClientError, match="valid Git branch"):
        client.select_dev_ref(_client_settings(config_path), "feature/bad branch")

    assert config_path.read_bytes() == original_bytes


def test_apply_failure_restores_original_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "bundles.json"
    original_bytes = _write_config(config_path)
    calls = 0

    def mocked_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        nonlocal calls
        calls += 1
        if command[0] == "git":
            return subprocess.CompletedProcess(args=command, returncode=0)
        if calls == 2:
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(client.subprocess, "run", mocked_run)

    with pytest.raises(client.BundleClientError, match="restored 'feature/initial'"):
        client.select_dev_ref(_client_settings(config_path), "feature/next")

    assert config_path.read_bytes() == original_bytes
    assert calls == 3


def test_bundle_config_requires_all_three_unique_bundle_names(tmp_path: Path) -> None:
    config_path = tmp_path / "bundles.json"
    _write_config(config_path, _bundle_config()[:2])

    with pytest.raises(client.BundleClientError, match="lakehouse-prod"):
        client.show_selected_ref(config_path)


def test_example_bundle_config_has_isolated_environment_dag_paths() -> None:
    bundles = json.loads((REPOSITORY_ROOT / "airflow_bundle_config.example.json").read_text(encoding="utf-8"))
    by_name = {bundle["name"]: bundle for bundle in bundles}

    assert set(by_name) == {"lakehouse-dev", "lakehouse-uat", "lakehouse-prod"}
    assert by_name["lakehouse-uat"]["kwargs"]["tracking_ref"] == "uat"
    assert by_name["lakehouse-prod"]["kwargs"]["tracking_ref"] == "main"
    assert by_name["lakehouse-dev"]["kwargs"]["tracking_ref"].startswith("feature/")
    environment_bundles = (
        "lakehouse-dev",
        "lakehouse-uat",
        "lakehouse-prod",
    )
    for bundle_name in environment_bundles:
        sparse_dirs = by_name[bundle_name]["kwargs"]["sparse_dirs"]
        assert "dags" in sparse_dirs
        assert "configs" in sparse_dirs
        assert "notebooks" in sparse_dirs


def test_dag_factory_reuses_spark_container_for_bundle_workloads() -> None:
    dag_path = REPOSITORY_ROOT / "dags" / "test_environment.py"
    source = dag_path.read_text(encoding="utf-8")
    factory_path = REPOSITORY_ROOT / "dags" / "dag_factory.py"
    factory = factory_path.read_text(encoding="utf-8")

    assert dag_path.is_file()
    assert 'dag_name="init_environment"' in source
    assert '"task_name": "test_environment_first"' in source
    assert '"task_name": "test_environment_second"' in source
    assert '"task_name": "count_sample_rows"' in source
    assert '"entrypoint_file": "count_sample_rows.py"' in source
    assert '"runs_after": ("test_environment_first",)' in source
    assert "schedule=None" in source
    assert "create_spark_dag(" in source
    assert 'task_id="validate_environment"' in factory
    assert 'task_id="create_cluster"' in factory
    assert 'task_id="stop_cluster"' in factory
    assert "_submit_spark_job" in factory
    assert "TriggerRule.ALL_DONE" in factory
    assert '"/opt/spark/bin/spark-submit"' in factory
    assert 'str(CONTAINER_BUNDLE_ROOT / "configs")' in factory
    assert '"spark-files"' not in factory
    assert "identity_for_bundle(DAGS_DIR)" in factory
    assert "dag_id_prefix=dag_id_prefix" in factory
    assert "SparkSubmitOperator" not in factory
    assert "RELEASE_ID" not in factory


def test_spark_failure_output_redacts_credentials() -> None:
    secret = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    jwt = "eyJhbGciOiJSUzI1NiJ9.payloadsegment.signaturesegment"
    output = f'Authorization: Bearer {jwt}\naccess_token="{secret}" token={secret}'

    redacted = redact_spark_output(output)

    assert jwt not in redacted
    assert secret not in redacted
    assert "<redacted>" in redacted


def test_settings_reject_shell_string_apply_command(tmp_path: Path) -> None:
    settings_path = tmp_path / "client.yml"
    settings_path.write_text(
        "bundle_config_path: /tmp/bundles.json\n" "allowed_branch_prefixes: [feature/]\n" "apply_command: 'apply --config {config_path}'\n",
        encoding="utf-8",
    )

    with pytest.raises(client.BundleClientError, match="list of command arguments"):
        client.load_client_settings(settings_path)

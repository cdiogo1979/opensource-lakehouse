"""Safely select the feature branch used by Airflow's development bundle."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

import yaml


PROTECTED_REFS = frozenset({"dev", "uat", "main"})
DEV_BUNDLE_NAME = "lakehouse-dev"
APPLY_CONFIG_PLACEHOLDER = "{config_path}"


class BundleClientError(Exception):
    """Raised when bundle configuration cannot be safely updated."""


def load_client_settings(settings_path: Path) -> dict[str, Any]:
    """Load and validate the non-secret branch-client settings.

    Args:
        settings_path: YAML file containing the deployment-owned config path,
            bundle name, optional branch-prefix policy, and apply command.

    Returns:
        Validated settings with an absolute bundle config path.

    Raises:
        BundleClientError: If the settings file is missing or invalid.
    """
    try:
        settings = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise BundleClientError(f"Cannot read client settings: {error}") from error

    if not isinstance(settings, dict):
        raise BundleClientError("Client settings must be a YAML mapping")

    config_value = settings.get("bundle_config_path")
    if not isinstance(config_value, str) or not config_value.strip():
        raise BundleClientError("bundle_config_path must be a non-empty string")
    config_path = Path(config_value).expanduser()
    if not config_path.is_absolute():
        config_path = (settings_path.parent / config_path).resolve()
    settings["bundle_config_path"] = config_path

    if settings.get("dev_bundle_name", DEV_BUNDLE_NAME) != DEV_BUNDLE_NAME:
        raise BundleClientError(f"dev_bundle_name must be {DEV_BUNDLE_NAME!r}")
    settings["dev_bundle_name"] = DEV_BUNDLE_NAME

    prefixes = settings.get("allowed_branch_prefixes", [])
    if not isinstance(prefixes, list) or not prefixes or any(
        not isinstance(prefix, str) or not prefix for prefix in prefixes
    ):
        raise BundleClientError(
            "allowed_branch_prefixes must contain at least one non-empty feature-branch prefix"
        )
    settings["allowed_branch_prefixes"] = prefixes

    apply_timeout = settings.get("apply_timeout_seconds", 300)
    if not isinstance(apply_timeout, int) or apply_timeout < 1:
        raise BundleClientError("apply_timeout_seconds must be a positive integer")
    settings["apply_timeout_seconds"] = apply_timeout

    apply_command = settings.get("apply_command")
    if not isinstance(apply_command, list) or not apply_command or any(
        not isinstance(part, str) or not part for part in apply_command
    ):
        raise BundleClientError("apply_command must be a non-empty list of command arguments")
    if not any(APPLY_CONFIG_PLACEHOLDER in part for part in apply_command):
        raise BundleClientError(
            f"apply_command must include {APPLY_CONFIG_PLACEHOLDER}"
        )
    settings["apply_command"] = apply_command
    return settings


def _load_bundle_config(config_path: Path) -> tuple[list[dict[str, Any]], bytes]:
    """Read a Git bundle config list and return it with its original bytes."""
    try:
        original_bytes = config_path.read_bytes()
        bundles = json.loads(original_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BundleClientError(f"Cannot read bundle config: {error}") from error

    if not isinstance(bundles, list):
        raise BundleClientError("Bundle config must be a JSON list")
    names: list[str] = []
    for bundle in bundles:
        if not isinstance(bundle, dict):
            raise BundleClientError("Every bundle entry must be a JSON object")
        name = bundle.get("name")
        kwargs = bundle.get("kwargs")
        if not isinstance(name, str) or not isinstance(kwargs, dict):
            raise BundleClientError("Each bundle requires a name and kwargs object")
        names.append(name)
    if len(names) != len(set(names)):
        raise BundleClientError("Bundle names must be unique")
    if names.count(DEV_BUNDLE_NAME) != 1:
        raise BundleClientError(f"Bundle config must contain exactly one {DEV_BUNDLE_NAME!r}")
    for name in ("lakehouse-uat", "lakehouse-prod"):
        if names.count(name) != 1:
            raise BundleClientError(f"Bundle config must contain exactly one {name!r}")
    return bundles, original_bytes


def _dev_bundle(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the configured development bundle entry."""
    return next(bundle for bundle in bundles if bundle["name"] == DEV_BUNDLE_NAME)


def show_selected_ref(config_path: Path) -> str:
    """Return the currently configured development tracking ref.

    Args:
        config_path: JSON `dag_bundle_config_list` file.

    Returns:
        Current `lakehouse-dev` tracking ref.

    Raises:
        BundleClientError: If the bundle configuration is invalid.
    """
    bundles, _ = _load_bundle_config(config_path)
    tracking_ref = _dev_bundle(bundles)["kwargs"].get("tracking_ref")
    if not isinstance(tracking_ref, str) or not tracking_ref:
        raise BundleClientError("lakehouse-dev has no configured tracking_ref")
    return tracking_ref


def validate_feature_ref(
    tracking_ref: str,
    allowed_prefixes: Sequence[str] = (),
) -> None:
    """Validate a requested Git branch without contacting the Git server.

    Args:
        tracking_ref: Branch name selected for the development bundle.
        allowed_prefixes: Optional required branch prefixes, such as
            ``("feature/",)``.

    Raises:
        BundleClientError: If the ref is protected, malformed, or outside the
            configured prefix policy.
    """
    if not isinstance(tracking_ref, str) or not tracking_ref.strip():
        raise BundleClientError("tracking ref must be a non-empty branch name")
    if tracking_ref in PROTECTED_REFS:
        raise BundleClientError("dev bundle cannot track a protected ref")
    if allowed_prefixes and not any(
        tracking_ref.startswith(prefix) for prefix in allowed_prefixes
    ):
        raise BundleClientError("tracking ref does not match the configured branch prefix")
    try:
        result = subprocess.run(
            ["git", "check-ref-format", f"refs/heads/{tracking_ref}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BundleClientError("Unable to validate the branch name with Git") from error
    if result.returncode != 0:
        raise BundleClientError("tracking ref is not a valid Git branch name")


def _atomic_write(config_path: Path, content: bytes) -> None:
    """Replace a config file atomically while preserving its mode."""
    temporary_path: Path | None = None
    try:
        file_mode = config_path.stat().st_mode & 0o777
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=config_path.parent, prefix=f".{config_path.name}.", delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.chmod(temporary_path, file_mode)
        os.replace(temporary_path, config_path)
    except OSError as error:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise BundleClientError(f"Cannot atomically update bundle config: {error}") from error


def select_dev_ref(settings: dict[str, Any], tracking_ref: str) -> tuple[str, str]:
    """Select and apply a feature ref for the dev bundle only.

    Args:
        settings: Validated client settings from ``load_client_settings``.
        tracking_ref: Requested feature branch name.

    Returns:
        A pair containing the old and new dev refs after successful apply.

    Raises:
        BundleClientError: If validation, configuration update, or apply fails.
    """
    validate_feature_ref(tracking_ref, settings["allowed_branch_prefixes"])
    config_path: Path = settings["bundle_config_path"]
    bundles, original_bytes = _load_bundle_config(config_path)
    dev_bundle = _dev_bundle(bundles)
    previous_ref = dev_bundle["kwargs"].get("tracking_ref")
    if not isinstance(previous_ref, str) or not previous_ref:
        raise BundleClientError("lakehouse-dev has no configured tracking_ref")
    if tracking_ref == previous_ref:
        return previous_ref, tracking_ref

    uat_before = json.dumps(next(b for b in bundles if b["name"] == "lakehouse-uat"))
    prod_before = json.dumps(next(b for b in bundles if b["name"] == "lakehouse-prod"))
    dev_bundle["kwargs"]["tracking_ref"] = tracking_ref
    if (
        json.dumps(next(b for b in bundles if b["name"] == "lakehouse-uat")) != uat_before
        or json.dumps(next(b for b in bundles if b["name"] == "lakehouse-prod")) != prod_before
    ):
        raise BundleClientError("Refusing update because UAT or production config changed")

    updated_bytes = (json.dumps(bundles, indent=2) + "\n").encode("utf-8")
    command = [
        argument.replace(APPLY_CONFIG_PLACEHOLDER, str(config_path))
        for argument in settings["apply_command"]
    ]
    _atomic_write(config_path, updated_bytes)
    try:
        subprocess.run(
            command,
            check=True,
            shell=False,
            capture_output=True,
            text=True,
            timeout=settings["apply_timeout_seconds"],
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        try:
            _atomic_write(config_path, original_bytes)
            subprocess.run(
                command,
                check=True,
                shell=False,
                capture_output=True,
                text=True,
                timeout=settings["apply_timeout_seconds"],
            )
        except (BundleClientError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as rollback_error:
            raise BundleClientError(
                "Apply failed and restoring the previous bundle config could not be fully applied"
            ) from rollback_error
        raise BundleClientError(
            f"Applying the selected branch failed; restored {previous_ref!r}"
        ) from error
    return previous_ref, tracking_ref


def build_parser() -> argparse.ArgumentParser:
    """Create the command line parser for the bundle client."""
    parser = argparse.ArgumentParser(
        description="Select the feature branch tracked by Airflow's dev bundle."
    )
    parser.add_argument(
        "--settings",
        type=Path,
        required=True,
        help="Path to deployment-owned, non-secret client settings YAML.",
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    subparsers.add_parser("show", help="Show the currently selected dev branch.")
    select_parser = subparsers.add_parser("select", help="Select a feature branch for dev.")
    select_parser.add_argument("--branch", required=True, help="Git feature branch name.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the branch-selection client and return a process exit status."""
    args = build_parser().parse_args(argv)
    try:
        settings = load_client_settings(args.settings)
        config_path: Path = settings["bundle_config_path"]
        if args.operation == "show":
            print(f"lakehouse-dev tracking_ref: {show_selected_ref(config_path)}")
            return 0
        previous_ref, selected_ref = select_dev_ref(settings, args.branch)
        if previous_ref == selected_ref:
            print(f"lakehouse-dev already tracks {selected_ref!r}; no apply was needed")
        else:
            print(
                f"Updated lakehouse-dev tracking_ref from {previous_ref!r} to "
                f"{selected_ref!r}; deployment apply succeeded. Airflow fetch/parse "
                "readiness must be confirmed in Airflow."
            )
        return 0
    except BundleClientError as error:
        print(f"Branch selection failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

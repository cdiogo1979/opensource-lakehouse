"""Load and validate environment-specific lakehouse configuration."""

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterator, Mapping, Optional, Union

import yaml

SUPPORTED_ENVIRONMENTS = frozenset({"dev", "uat", "prod"})
REQUIRED_KEYS = ("storage_path", "database_name")


@dataclass(frozen=True)
class EnvironmentConfig(Mapping[str, Any]):
    """Validated settings for one environment, exposed as a read-only mapping.

    Attributes:
        environment: Supported environment identifier (`dev`, `uat`, or `prod`).
        settings: All settings from the environment YAML, including extra keys
            and nested mappings not interpreted by the loader.
    """

    environment: str
    settings: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Freeze nested settings even when the value is constructed directly."""
        object.__setattr__(self, "settings", _freeze_yaml_value(self.settings))

    def __getitem__(self, key: str) -> Any:
        """Return a top-level setting by key.

        Args:
            key: YAML setting name.

        Returns:
            The selected setting, including nested mappings and sequences.
        """
        return self.settings[key]

    def __iter__(self) -> Iterator[str]:
        """Iterate over keys present in the selected YAML file.

        Yields:
            Top-level YAML setting names.
        """
        return iter(self.settings)

    def __len__(self) -> int:
        """Return the number of top-level settings in the YAML file.

        Returns:
            Count of top-level YAML settings.
        """
        return len(self.settings)

    def to_dict(self) -> dict:
        """Return a mutable copy of all settings using native dict/list values.

        Returns:
            A deep copy of the full YAML mapping. Nested mappings and sequences
            are converted to dictionaries and lists.
        """
        return _thaw_yaml_value(self.settings)


def _freeze_yaml_value(value: Any) -> Any:
    """Recursively freeze YAML mappings and sequences.

    Args:
        value: A value returned by PyYAML's safe loader.

    Returns:
        A read-only equivalent for mappings and sequences, or the unchanged
        scalar value.
    """
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_yaml_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_yaml_value(item) for item in value)
    return value


def _thaw_yaml_value(value: Any) -> Any:
    """Convert frozen YAML containers back to mutable Python containers.

    Args:
        value: A scalar or frozen YAML mapping/sequence.

    Returns:
        A mutable recursive copy using dictionaries and lists.
    """
    if isinstance(value, Mapping):
        return {key: _thaw_yaml_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_yaml_value(item) for item in value]
    return value


def load_environment_config(environment: str, config_dir: Optional[Union[str, Path]] = None) -> EnvironmentConfig:
    """Load exactly one environment YAML file and validate its required values.

    Args:
        environment: Environment identifier. Only `dev`, `uat`, and `prod` are
            accepted; no environment is inferred or selected by default.
        config_dir: Optional directory containing the environment YAML files.
            By default, resolves `configs/` from the repository root relative
            to this module.

    Returns:
        An immutable `EnvironmentConfig` populated from the selected file.

    Raises:
        ValueError: If the environment is unsupported, YAML is malformed, its
            root is not a mapping, or a required key is missing or invalid.
        FileNotFoundError: If the selected environment file does not exist.
    """
    if not isinstance(environment, str) or environment not in SUPPORTED_ENVIRONMENTS:
        supported = ", ".join(sorted(SUPPORTED_ENVIRONMENTS))
        raise ValueError(f"Unsupported environment {environment!r}; expected one of: {supported}.")

    directory = Path(config_dir) if config_dir is not None else Path(__file__).resolve().parents[2] / "configs"
    config_path = directory / f"{environment}.yml"

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            values = yaml.safe_load(config_file)
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Configuration file for environment {environment!r} was not found: " f"{config_path}") from error
    except yaml.YAMLError as error:
        raise ValueError(f"Configuration file for environment {environment!r} contains invalid YAML: " f"{config_path}") from error

    if not isinstance(values, dict):
        raise ValueError(f"Configuration file for environment {environment!r} must contain a YAML mapping: " f"{config_path}")

    for key in REQUIRED_KEYS:
        value = values.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Configuration key {key!r} must be a non-empty string in {config_path}.")
    return EnvironmentConfig(
        environment=environment,
        settings=_freeze_yaml_value(values),
    )

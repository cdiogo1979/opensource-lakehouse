# Domain Entities: `workload-foundation`

This repository foundation has no business-domain entities. Its configuration contract is represented by the following technical value object.

## `EnvironmentConfig`
- `environment: str` — one of `dev`, `uat`, or `prod`.
- `settings: Mapping[str, Any]` — the complete selected YAML mapping, including arbitrary top-level keys and nested values.
- Mapping access — applications retrieve values with `config["key"]`, `config.get("key")`, and nested mapping access such as `config["spark"]["executor"]["memory"]`.
- Required current workload keys — `storage_path: str` is a non-empty configured root ending in `/`; `database_name: str` is a non-empty target database/catalog namespace and simple identifier. Additional keys are not rejected by the loader.

The loader constructs this value only after validating the selected YAML. The mapping and nested mappings/sequences are exposed read-only; YAML sequences appear as tuples. `to_dict()` returns a mutable deep copy using dictionaries and lists. It contains no secrets or credentials.

## `SampleRecord`
The `init_environment` smoke check uses a fixed, synthetic record schema solely to verify catalog and storage access after initialization. The precise columns and example rows are implementation details selected during Code Generation; they do not represent a business entity.

## Initialization Targets
The workload does not introduce a new business entity. Its technical targets are the configured `EnvironmentConfig.database_name` namespace and `EnvironmentConfig.storage_path` logical root/prefix. The smoke table is isolated at the fixed child path `storage_path + "sample_spark_job_output"` and table `database_name.sample_spark_job_output`.

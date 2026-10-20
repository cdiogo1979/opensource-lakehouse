# Airflow Git DAG Bundles

## Bundle layout

`airflow_bundle_config.example.json` demonstrates three `GitDagBundle` entries for one Airflow 3 deployment:

| Bundle | Tracking ref | DAG directory |
|---|---|---|
| `lakehouse-dev` | Selected feature branch | `dags/` |
| `lakehouse-uat` | `uat` | `dags/` |
| `lakehouse-prod` | `main` | `dags/` |

Each bundle also includes `configs/` and `notebooks/` so a DAG run can use the artifacts from the same recorded commit. The repository root is the bundle root (`subdir` is omitted). Update the example repository URL and Airflow Git connection ID for the deployment. Store Git credentials in the Airflow connection or secrets backend; never place credentials in the bundle JSON.

All bundles check out the same repository paths (`dags/`, `configs/`, and `notebooks/`) at their configured refs. The Git ref selects the code version; the stable Airflow bundle name selects the DAG ID prefix and workload config: `lakehouse-main`/`lakehouse-prod` creates a `main-` DAG ID and uses `prod.yml`, `lakehouse-uat` creates `uat-` and uses `uat.yml`, and all other bundle names create `dev-` and use `dev.yml`. This keeps feature branches on the dev environment when the dev bundle client changes its tracking ref. The shared DAG factory derives the bundle name from the Git bundle checkout path. Airflow may parse from `<bundle-storage>/<bundle-name>/tracking_repo/...` and use `<bundle-storage>/<bundle-name>/versions/<commit>/...` for pinned versions. These path conventions are implementation details and should be rechecked when upgrading or changing bundle storage configuration. Config and workload files remain branch-versioned and all environment YAML files may coexist in the repository.

Install compatible `apache-airflow-providers-git` and `apache-airflow-providers-docker` releases in the DAG processor and task execution components. Configure the JSON list as `[dag_processor] dag_bundle_config_list` (for example through `AIRFLOW__DAG_PROCESSOR__DAG_BUNDLE_CONFIG_LIST`). Keep bundle versioning enabled and configure a suitable refresh interval. Disable or leave the default local DAG bundle empty so it does not discover duplicate DAG files.

The `refresh_interval` in the example is illustrative. A branch commit appears after Airflow fetches it and successfully parses the DAG. Each run is associated with a bundle commit; preserve that version when rerunning unless you intentionally select the latest version.

## Configure the branch-selection client

The client changes the development bundle's `tracking_ref`; it does not push or merge branches. Copy `airflow_bundle_client.example.yml` to a deployment-owned location and set:

- `bundle_config_path`: writable JSON `dag_bundle_config_list` source file used by the deployment apply operation.
- `dev_bundle_name`: keep `lakehouse-dev`.
- `allowed_branch_prefixes`: required list of feature branch prefixes, such as `feature/`; selected refs must match one.
- `apply_command`: an argv list for a trusted deployment command. It must apply the updated JSON to Airflow and perform the deployment-specific reload/restart needed for the new `tracking_ref` to take effect. Include `{config_path}` as the argument that receives the updated JSON file. Do not use a shell command string or store secrets in this file.

Airflow's built-in UI does not provide a `tracking_ref` selector. The deployment command is platform-specific because Airflow may receive this setting through environment variables, an Airflow config file, Helm, Docker Compose, or another deployment manager. Configure the client on an operator-controlled host with access to the bundle config and deployment command. Limit access to trusted operators; selected DAG code executes with Airflow's privileges.

## Select and verify a feature branch

```bash
python3 airflow_bundle_client.py --settings /path/to/client.yml show
python3 airflow_bundle_client.py --settings /path/to/client.yml select --branch feature/my-change
```

The client rejects invalid Git refs, protected refs (`dev`, `uat`, `main`), and refs outside the configured feature prefixes. It modifies only `lakehouse-dev`, writes the config atomically, runs the configured apply command without a shell, and restores the previous config if apply fails. A successful client command means the deployment apply command succeeded; it does not mean Airflow has fetched or parsed the branch.

After switching, confirm in Airflow that the dev DAG is available from the intended branch and inspect the DAG/run bundle version before triggering it. The selected feature branch must contain `dags/`, the environment config, and the Spark workload/helpers under `notebooks/`; it should preserve the dev environment ID. UAT and production continue tracking their fixed refs and retain their own environment IDs in their branch versions.

## Spark application path requirement

The sample DAG derives the repository root from its location inside the bundle version. It validates the environment config, creates one reusable Spark Docker container with the bundle mounted read-only, submits each named workload sequentially with `/opt/spark/bin/spark-submit`, then removes the container in a cleanup task that runs after success or failure. Declare workloads as `(task_name, entrypoint_file)` pairs; the same entrypoint can appear under different task names. For example:

```python
dag = create_spark_dag(
    dag_name="init_environment",
    workloads=(
        ("initialize_environment_first", "init_environment.py"),
        ("initialize_environment_second", "init_environment.py"),
    ),
    schedule=None,
)
```

Each submission starts a separate Spark application in `local[*]` mode inside the shared container. This is a single-container setup, not a distributed Spark master/worker cluster. The image must include a compatible Spark runtime and PyYAML. Configure `LAKEHOUSE_SPARK_IMAGE`, `LAKEHOUSE_SPARK_MASTER` (defaults to `local[*]`), `LAKEHOUSE_DOCKER_URL`, and `LAKEHOUSE_SPARK_DOCKER_NETWORK` in Airflow. The Docker daemon must be able to access the same bundle-checkout path that the task runner resolved. Verify this host path mapping and selected bundle-commit version before using the setup for shared environments.

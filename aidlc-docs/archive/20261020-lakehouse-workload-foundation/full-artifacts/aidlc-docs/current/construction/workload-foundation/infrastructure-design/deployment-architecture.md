# Deployment Architecture: `workload-foundation`

## Runtime Topology

Airflow and the Spark job runtime are shared by development, UAT, and production. Airflow reads the DAG from versioned Git DAG Bundles and uses `DockerOperator` to launch a Spark job image. The container runs `spark-submit` with the Python workload and YAML from the run's bundle commit, using a deployment-configured Spark master. The bundle name selects the DAG prefix and config environment: main/prod maps to `prod`, UAT to `uat`, and other names to `dev`. `init_environment` creates the configured namespace idempotently before writing the dedicated smoke table; the table write creates the object prefix.

Logical flow: an operator starts the bundle-scoped manual DAG; Airflow executes the run from its recorded Git bundle version; the DAG validates the mapped environment config and launches a Spark job container with the bundle checkout mounted read-only; `spark-submit` runs the workload using the configured Spark master; the job creates its namespace and writes the smoke table to configured targets.

This flow does not specify network placement, AWS account boundaries, a catalog implementation, Spark manager, or deployment mechanism.

## Deployment Boundaries

### Repository-managed

- Environment YAML files with non-secret `storage_path` and `database_name` values.
- Shared config loader, `init_environment` Spark Python workload, and manual Airflow DAG.
- No infrastructure provisioning definitions are included in this unit.

### Platform-managed

- Shared Airflow deployment, Git DAG Bundle configuration/versioning, provider packages, Git connection, Docker daemon/socket access, and Spark job image.
- Spark runtime/master, Python/YAML dependencies, S3 filesystem connector, network access, and availability/scaling.
- AWS identity and S3 authorization, S3 buckets/prefixes, catalog/metastore and database/table permissions.
- Secret backend, network connectivity, logging retention, and operational monitoring.

## Environment Selection and Data Boundaries

Each bundle checks out the same root `dags/` path from its selected Git ref. The bundle name provides environment identity: `lakehouse-main`/`lakehouse-prod` maps to `prod` config and `main-` DAG IDs, `lakehouse-uat` maps to `uat`, and every other name maps to `dev`. The shared factory derives the name from the bundle checkout path and passes the matching environment to the Spark workload. UAT and production share compute and orchestration but must use their intended separate configured data targets and appropriately scoped permissions.

The development target topology was not specified. Its concrete runtime target and access arrangements are deployment inputs.

## Release and Runtime Sequence

1. Provide concrete non-secret values in the environment configuration files, including each intended S3 location and database name.
2. Configure the Docker daemon connection, Spark job image, Spark master/network and external secret/identity mechanisms.
3. Ensure the shared Spark runtime has compatible Python, YAML, Spark, and S3 filesystem support, and can access the shared config loader and workload files.
4. Provision catalog/database access and environment-appropriate S3 permissions for the Spark identity.
5. Confirm that Airflow has fetched and parsed the intended bundle ref/version; for development, use the branch-selection client to choose the feature branch first.
6. Manually trigger the DAG for the intended environment and review Airflow task status, bundle version, and Spark logs.

The repository does not select an Airflow executor, bundle config apply/reload command, Docker daemon endpoint, Spark image/master/network, AWS region/account, bucket, URI scheme, or catalog product. Those values must be established by platform owners. The Docker daemon must see the run-versioned bundle checkout path for the read-only bind mount.

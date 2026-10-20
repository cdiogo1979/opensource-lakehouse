# Shared Infrastructure: `workload-foundation`

UAT and production use the same externally managed Airflow and Spark infrastructure. Environment-specific YAML files select the storage path and database/catalog name used by the workload. This is data-target separation on shared compute and orchestration; it does not provide separate Airflow or Spark service boundaries.

Platform owners are responsible for ensuring configured UAT and production targets are correct and that the Spark identity has only the intended access. Airflow connection settings, credentials, network controls, Spark runtime, S3 connector, and catalog are managed outside this repository. Exact account, region, bucket, connection, and catalog values remain deployment inputs.

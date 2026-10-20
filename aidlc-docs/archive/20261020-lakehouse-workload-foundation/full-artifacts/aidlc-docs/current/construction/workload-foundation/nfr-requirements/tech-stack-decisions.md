# Technology Decisions: `workload-foundation`

| Area | Decision | Rationale / constraint |
|---|---|---|
| Workload language | Python | User requested Python Spark scripts exported from Jupyter notebooks. |
| Spark execution | Airflow `DockerOperator` launches a configured job image that runs `spark-submit` | The image/master/network are deployment configuration; the container uses bundle-versioned workload and config files. |
| Configuration serialization | YAML via PyYAML | User selected one YAML file per environment. PyYAML is used by the shared config loader. |
| Property-based testing | Hypothesis | Python framework supports generated inputs and shrinking for loader invariants and the deterministic overwrite contract; include it in `requirements-dev.txt`. |
| Orchestration | Apache Airflow | User-selected orchestrator; sample DAG has `schedule=None` and requires an explicit environment. |
| CI/CD | Jenkins Pipeline | User selected Jenkins; deployment targets and credentials are supplied externally. |
| Runtime versions | Not pinned in this repository | Python, Airflow, Spark, and provider versions are managed by external platforms; no compatibility versions were supplied. |

## PBT-09 Compliance
- **Status**: Compliant.
- **Framework**: Hypothesis for Python.
- **Applicable properties**: Config environment isolation, required-key invariants, and invalid-input failure behavior described by Functional Design.
- **Dependency handling**: Hypothesis is included as a development/test dependency in `requirements-dev.txt` during authorized Code Generation.

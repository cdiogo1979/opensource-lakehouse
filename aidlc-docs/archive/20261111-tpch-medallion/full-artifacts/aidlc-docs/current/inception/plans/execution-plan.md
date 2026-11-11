# Execution Plan — TPC-H Medallion Subproject

## Detailed Analysis Summary
- **Transformation type**: a new subproject (two notebooks, one workflow, config keys) plus documentation of conventions; no platform change planned.
- **Impact**: new Iceberg tables in each environment's namespace (`tpch_<entity>_db_brz`, `tpch_<entity>`); a new DAG `default-<env>-tpch_medallion`; `configs/*.yml` gain `checkpoint_path`; AGENTS.md, README and the notebook-structure test change; `sample` is unchanged.
- **Risk**: medium.
  - **Not yet proven** (Application Design probes):
    - writing a Spark checkpoint at `checkpoint_path` (`s3a://` in the product bucket) from an Airflow run and from Jupyter, without credentials beyond Polaris';
    - Iceberg's streaming source on the bronze table through Polaris (`trigger(availableNow=True)`, starting from a timestamp for the lookback);
    - creating an Iceberg table with an explicit location inside the namespace, and `MERGE INTO` it, as the product writer;
    - DuckDB rows (Arrow) into a Spark DataFrame in the run container.
  - **Effects**: tables can't be dropped by the writer; a wrong schema would need an owner or Polaris to fix.
- **Rollback**: revert the commits; created tables stay (writers can't drop them).

## Workflow Visualization
```mermaid
flowchart TD
    Start(["User Request"])
    subgraph INCEPTION["INCEPTION PHASE"]
        WD["Workspace Detection<br/><b>COMPLETED</b>"]
        RE["Reverse Engineering<br/><b>COMPLETED</b>"]
        RA["Requirements Analysis<br/><b>COMPLETED</b>"]
        US["User Stories<br/><b>SKIP</b>"]
        WP["Workflow Planning<br/><b>IN PROGRESS</b>"]
        AD["Application Design<br/><b>EXECUTE</b>"]
        UG["Units Generation<br/><b>SKIP</b>"]
    end
    subgraph CONSTRUCTION["CONSTRUCTION PHASE"]
        FD["Functional Design<br/><b>EXECUTE</b>"]
        NFR["NFR Requirements and Design<br/><b>SKIP</b>"]
        ID["Infrastructure Design<br/><b>SKIP</b>"]
        CG["Code Generation<br/><b>EXECUTE</b>"]
        BT["Build and Test<br/><b>EXECUTE</b>"]
    end
    subgraph DEPLOY["DEPLOY PHASE"]
        DH["Deploy<br/><b>PREPARE HANDOFF</b>"]
    end
    Start --> WD --> RE --> RA --> WP --> AD --> FD --> CG --> BT --> DH --> End(["Complete"])

    style WD fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style RE fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style RA fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style WP fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style US fill:#BDBDBD,stroke:#424242,stroke-width:2px,stroke-dasharray: 5 5,color:#000
    style UG fill:#BDBDBD,stroke:#424242,stroke-width:2px,stroke-dasharray: 5 5,color:#000
    style NFR fill:#BDBDBD,stroke:#424242,stroke-width:2px,stroke-dasharray: 5 5,color:#000
    style ID fill:#BDBDBD,stroke:#424242,stroke-width:2px,stroke-dasharray: 5 5,color:#000
    style AD fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style FD fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style CG fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style BT fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style DH fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style Start fill:#CE93D8,stroke:#6A1B9A,stroke-width:3px,color:#000
    style End fill:#CE93D8,stroke:#6A1B9A,stroke-width:3px,color:#000
    linkStyle default stroke:#333,stroke-width:2px
```
Text alternative: Workspace Detection, Reverse Engineering and Requirements Analysis are completed. Workflow Planning leads to Application Design, Functional Design, Code Generation, Build and Test, and the Deploy handoff. User Stories, Units Generation, NFR and Infrastructure Design are skipped.

## Phases
- [ ] User Stories: SKIP. One persona (the data engineer); the requirements state the behavior.
- [ ] Application Design: **EXECUTE**. The four probes above (in dev, as the platform's writer path allows, and in throwaway sessions); notebook components and their sections; how the checkpoint location, table locations and names are derived; the widget and argument declarations.
- [ ] Units Generation: SKIP. One unit, `tpch`.
- [ ] Functional Design: **EXECUTE**. Bronze schema and columns; the merge-key map; latest-row selection; merge conditions; lookback and checkpoint reset rules; argument validation; log summaries; properties.
- [ ] NFR Requirements, NFR Design, Infrastructure Design: SKIP. Security and Resiliency off; no infrastructure change (unless the checkpoint probe forces one, which goes back to the user).
- [ ] Code Generation: **EXECUTE**. Notebooks, workflow, configs, AGENTS.md, README, tests.
- [ ] Build and Test: **EXECUTE**. `scripts/code_quality.sh all`, pytest, the platform validator; push only with approval; a UAT run of `tpch_medallion` twice (incremental and with a lookback); Jenkins; a Jupyter check by the user.
- [ ] Deploy: **EXECUTE**, as a handoff.

## Canonical Knowledge Impact Inventory
| Canonical path | Action | Requirement | Reason |
|---|---|---|---|
| `aidlc-docs/knowledge/tpch/application-design.md` | CREATE | FR-1 to FR-6 | New subproject (AGENTS.md: one application design per subproject) |
| `aidlc-docs/knowledge/tpch/functional-design/medallion-load.md` | CREATE | FR-3, FR-4 | The bronze and silver load rules (one functional design per component) |
| `aidlc-docs/knowledge/opensource-lakehouse/application-design.md` | UPDATE | FR-2, FR-7, Q8 | Replace the stale content (Nessie, DockerOperator, repository DAG factory) with the current repository-level design: platform contract, shared helpers, notebook standard, naming conventions, subprojects |
| `aidlc-docs/knowledge/opensource-lakehouse/functional-design/workload-foundation.md` | UPDATE | FR-7, Q8 | The shared helpers as they are today (`job_runtime`, `cli.parse_task_args`, the Jupyter scripts, `config_loader`) |
| `aidlc-docs/knowledge/opensource-lakehouse/functional-design/jenkins-deployment.md` | UPDATE | Q8 | CI as it is today (platform validator, extras check, code quality, tests) |

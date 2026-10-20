# Unit Dependencies

## Dependency Matrix

| Unit | Depends on | Dependency reason |
|---|---|---|
| `workload-foundation` | None | Establishes the root configuration, notebook, and DAG artifact paths. |
| `jenkins-deployment` | `workload-foundation` | Bundle examples and branch client must use Unit 1's `configs/`, `dags/`, and `notebooks/` paths and workload conventions. |

## Coordination
- **Approach**: Sequential; Unit 1 first, then Unit 2.
- **Shared file**: `AGENTS.md` is edited by both units. Unit 1 establishes repository layout conventions; Unit 2 adds Jenkins deployment rules. Reconcile both edits in Unit 2.
- **External dependencies**: Airflow Git provider/configuration, branch-client apply/reload command, Git connection, Docker daemon, Spark job image/master/network are not provisioned by either unit.
- **Rollback**: Revert repository changes by unit; the branch client restores the previous dev tracking ref when its config apply fails.

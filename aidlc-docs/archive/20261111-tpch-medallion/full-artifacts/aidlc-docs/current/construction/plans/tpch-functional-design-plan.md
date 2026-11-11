# Functional Design Plan — tpch

## Steps
- [x] Read the approved requirements (FR-1 to FR-8, CR-1, CR-2) and Application Design (D1 to D8)
- [x] Probe DuckDB 1.5.6's TPC-H column types and Spark's inference (inference loses DECIMAL and DATE, so the schema is explicit)
- [x] Generate domain-entities.md
- [x] Generate business-rules.md (R1 to R20, P1 to P6)
- [x] Generate business-logic-model.md
- [x] Check against PBT partial (PBT-02, 03, 07, 08, 09)

## Decisions made here (for review)
| Item | Choice | Reason |
|---|---|---|
| Bronze schema | From DuckDB `DESCRIBE` through a type map; decimals through VARCHAR | Exact types and values (probe) |
| `scale_factor` column | `decimal(4,3)` | Covers 0.001 to 1 exactly |
| `bronze_ingestion_timestamp` | One UTC value per run | Rows of a run share it; R11 has no ties |
| Silver columns | The same as bronze | FR-4 "the same columns" |
| Lookback limit | 0 to 3650 days | Bounded; more is a full replay anyway |
| Tests | Pure rules with Hypothesis, Spark faked; Spark behavior live in Build and Test | Repository tests run without Spark |

## Questions
None open.

[Answer]: n/a (no questions)

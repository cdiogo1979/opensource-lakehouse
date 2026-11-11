# Application Design Plan — TPC-H Medallion Subproject

## Steps
- [x] Probe the four risks of the execution plan (`audit.md`): table creation at an explicit location, appends, `MERGE INTO` and DuckDB to Spark (first probe); checkpoint storage (paused, then solved by the platform intent `20261111-spark-s3-checkpoints`); the silver stream with `foreachBatch` MERGE, resume and the lookback reset on the new platform (second probe)
- [x] Record the platform answer as CR-2 in requirements.md
- [x] Generate components.md
- [x] Generate component-methods.md
- [x] Generate services.md
- [x] Generate component-dependency.md
- [x] Generate application-design.md (consolidated)
- [x] Check against requirements (FR-1 to FR-8, CR-1, CR-2), AGENTS.md and the PBT rules

## Questions
The design choices follow from the approved requirements (Q1 to Q8, CR-1, CR-2) and the probes; none is open. D3 and D8 were explained and decided by the user: names defined in each notebook; a lookback is a temporary workflow edit.

[Answer]: n/a (no open questions)

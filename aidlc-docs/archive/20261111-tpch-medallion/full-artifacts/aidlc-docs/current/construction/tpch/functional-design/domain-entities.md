# Domain Entities — tpch

## TPC-H entities
`region`, `nation`, `supplier`, `customer`, `part`, `partsupp`, `orders`, `lineitem` (the DuckDB `tpch` extension's tables, `CALL dbgen(sf=…)`).

| Entity | Merge key | DuckDB column types (probed, DuckDB 1.5.6) |
|---|---|---|
| region | `r_regionkey` | INTEGER, VARCHAR ×2 |
| nation | `n_nationkey` | INTEGER ×2, VARCHAR ×2 |
| supplier | `s_suppkey` | BIGINT, INTEGER, DECIMAL(15,2), VARCHAR |
| customer | `c_custkey` | BIGINT, INTEGER, DECIMAL(15,2), VARCHAR |
| part | `p_partkey` | BIGINT, INTEGER, DECIMAL(15,2), VARCHAR |
| partsupp | `ps_partkey`, `ps_suppkey` | BIGINT, DECIMAL(15,2), VARCHAR |
| orders | `o_orderkey` | BIGINT, INTEGER, DECIMAL(15,2), DATE, VARCHAR |
| lineitem | `l_orderkey`, `l_linenumber` | BIGINT, DECIMAL(15,2), DATE, VARCHAR |

## Bronze table `tpch_<entity>_db_brz`
- The entity's columns in DuckDB order, with Spark types from the type map (business-rules.md R5): INTEGER → `int`, BIGINT → `bigint`, DECIMAL(p,s) → `decimal(p,s)`, DATE → `date`, VARCHAR → `string`.
- `scale_factor` `decimal(4,3)`: the run's scale factor.
- `bronze_ingestion_timestamp` `timestamp`: one value per run (the run's start), the same for every row of the run.
- Append-only: one batch (one Iceberg snapshot) per run.

## Silver table `tpch_<entity>`
- The same columns as bronze (entity columns, `scale_factor`, `bronze_ingestion_timestamp`); one row per merge key, the newest seen in bronze.

## Names and locations (config `storage_path`, `catalog_name`, `database_name`, `checkpoint_path`)
| Item | Form | Dev example |
|---|---|---|
| Qualified name | `<catalog_name>.<database_name>.<table>` | `lakehouse_dev.default_lhdev.tpch_region` |
| Table location | `<storage_path>/<catalog_name>/<database_name>/<table>` | `s3a://bucket-default-dev/lakehouse_dev/default_lhdev/tpch_region` |
| Silver checkpoint | `<checkpoint_path>/tpch/<silver table>` | `s3ckpt://bucket-default-dev/checkpoints/tpch/tpch_region` |

## Task arguments
| Notebook | Argument | Default | Accepted |
|---|---|---|---|
| bronze | `entity` | required | one of the eight entities |
| bronze | `scale_factor` | `0.01` | 0.001 to 1, at most three decimals |
| silver | `entity` | required | one of the eight entities |
| silver | `silver_lookback_days` | `0` | an integer 0 to 3650 written in digits |

## Run logs (JSON; a start record before any work, then a summary)
- **Targets** (in both records): `environment`, `bucket`, `catalog`, `database`, `table`, `location`; silver also `source`, `source_location`, `checkpoint`, `checkpoint_bucket` (user, Code Generation: log the target and source tables, bucket and checkpoint locations).
- **Bronze summary**: `layer` (`bronze`), `entity`, `scale_factor`, `bronze_ingestion_timestamp` (ISO 8601 UTC), the targets, `rows_appended`, `created` (table created by this run).
- **Silver summary**: `layer` (`silver`), `entity`, `lookback_days`, `stream_from` (ISO 8601 UTC, or null), `checkpoint_reset`, the targets, `batches`, `rows_read`, `rows_merged` (rows after latest-per-key, offered to MERGE).

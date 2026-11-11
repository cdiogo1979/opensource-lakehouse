-- Deployed by the platform to UAT and prod as the product writer (see README, Materialized views).
CREATE MATERIALIZED VIEW ${mv_database}.mv_tpch_current
COMMENT 'TPC-H orders of the latest load day, with line items, customer, nation, region, part and supplier'
REFRESH ASYNC EVERY (INTERVAL 1 HOUR)
AS
SELECT
    o.o_orderkey, o.o_orderdate, o.o_orderstatus, o.o_orderpriority, o.o_totalprice, o.o_clerk,
    l.l_linenumber, l.l_quantity, l.l_extendedprice, l.l_discount, l.l_tax,
    l.l_extendedprice * (1 - l.l_discount) AS revenue,
    l.l_returnflag, l.l_linestatus, l.l_shipdate, l.l_commitdate, l.l_receiptdate, l.l_shipmode,
    c.c_custkey, c.c_name, c.c_mktsegment,
    n.n_name AS customer_nation, r.r_name AS customer_region,
    p.p_partkey, p.p_name, p.p_brand, p.p_type,
    s.s_suppkey, s.s_name AS supplier_name,
    o.bronze_ingestion_timestamp AS order_loaded_at
FROM ${catalog}.${namespace}.tpch_orders o
JOIN ${catalog}.${namespace}.tpch_lineitem l ON l.l_orderkey = o.o_orderkey
JOIN ${catalog}.${namespace}.tpch_customer c ON c.c_custkey = o.o_custkey
JOIN ${catalog}.${namespace}.tpch_nation n ON n.n_nationkey = c.c_nationkey
JOIN ${catalog}.${namespace}.tpch_region r ON r.r_regionkey = n.n_regionkey
JOIN ${catalog}.${namespace}.tpch_part p ON p.p_partkey = l.l_partkey
JOIN ${catalog}.${namespace}.tpch_supplier s ON s.s_suppkey = l.l_suppkey
WHERE DATE(o.bronze_ingestion_timestamp) = (SELECT MAX(DATE(bronze_ingestion_timestamp)) FROM ${catalog}.${namespace}.tpch_orders)

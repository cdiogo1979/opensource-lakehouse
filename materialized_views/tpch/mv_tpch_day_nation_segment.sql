-- Deployed by the platform to UAT and prod as the product writer (see README, Materialized views).
CREATE MATERIALIZED VIEW ${mv_database}.mv_tpch_day_nation_segment
COMMENT 'TPC-H sales per order date, customer region and nation, and market segment'
REFRESH ASYNC EVERY (INTERVAL 1 HOUR)
AS
SELECT
    o.o_orderdate AS order_date,
    r.r_name AS customer_region,
    n.n_name AS customer_nation,
    c.c_mktsegment AS market_segment,
    COUNT(DISTINCT o.o_orderkey) AS orders,
    COUNT(*) AS lines,
    SUM(l.l_quantity) AS quantity,
    SUM(l.l_extendedprice * (1 - l.l_discount)) AS revenue,
    AVG(l.l_discount) AS avg_discount
FROM ${catalog}.${namespace}.tpch_orders o
JOIN ${catalog}.${namespace}.tpch_lineitem l ON l.l_orderkey = o.o_orderkey
JOIN ${catalog}.${namespace}.tpch_customer c ON c.c_custkey = o.o_custkey
JOIN ${catalog}.${namespace}.tpch_nation n ON n.n_nationkey = c.c_nationkey
JOIN ${catalog}.${namespace}.tpch_region r ON r.r_regionkey = n.n_regionkey
GROUP BY o.o_orderdate, r.r_name, n.n_name, c.c_mktsegment

# Investigating a Slow SQL Query

I capture the exact query or fingerprint, parameters, execution frequency, latency distribution, rows returned, timeout, and database load.

I compare a normal period and check blocking/locks, connection pool saturation (how close a resource is to its limit), CPU, memory, storage I/O, cache hit rate, replication lag, and recent schema/statistics/deployment changes.
The database execution plan (`EXPLAIN` or the platform equivalent) shows scans, join order, estimates versus actual rows, sorting, spills, and index use.

I check whether filters are selective, data types match, functions prevent index use, too many rows/columns are returned, or an N+1 application pattern repeatedly calls the query.
Possible fixes include a carefully designed index, query rewrite, current statistics, pagination/batching, reduced result set, connection-pool correction, caching, partitioning, or data-model change.

Every index adds write/storage cost, so I test with production-like data, review locks and plan stability, deploy gradually, and measure query plus application latency afterward.

I keep rollback for schema/index changes and never kill sessions or add an index blindly without checking impact.


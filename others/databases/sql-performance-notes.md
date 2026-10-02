# Investigating a Slow SQL Query

I capture the exact query (or its fingerprint), the parameters, how often it runs, its latency distribution, how many rows it returns, any timeout, and the overall database load.

I compare against a normal period and check for blocking/locks, how saturated the connection pool is, CPU, memory, storage I/O, cache hit rate, replication lag, and any recent schema, statistics, or deployment change.

The database's execution plan (`EXPLAIN` or the platform's equivalent) shows scans, join order, estimated versus actual row counts, sorting, spills to disk, and whether indexes are actually being used.

I check whether the filters are selective enough, whether data types match, whether a function in the query is blocking index use, whether it's returning too many rows or columns, or whether the application is calling the query repeatedly in an N+1 pattern.

Possible fixes: a carefully designed index, rewriting the query, refreshing statistics, pagination or batching, cutting down the result set, fixing the connection pool, caching, partitioning, or changing the data model.

Every index adds cost on writes and storage, so I test with production-like data, check locks and plan stability, roll it out gradually, and measure both query and application latency afterward.

I always keep a rollback plan for schema or index changes, and I never kill a session or add an index blindly without checking the impact first.


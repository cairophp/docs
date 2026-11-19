# Repeated queries (N+1)

The N+1 pattern is one query per row in a loop where one query with a join
or `IN (...)` would do, often from an ORM that loads a relation lazily.
Cairo can warn about it with no code in the app:

```php
$app->repeatedQueries(10);   // warn when one request runs a statement 10 times or more
```

```
level=WARN msg="repeated query" route="GET /orders" count=50 query="SELECT * FROM items WHERE order_id = ?"
```

- Every statement counts, whatever runs it: PDO with any driver (MySQL,
  PostgreSQL, SQLite), through `PDO::query()`, `PDO::exec()` and
  `PDOStatement::execute()`, and `Cairo\Sql`. Laravel, Doctrine and other
  libraries built on PDO are covered.
- Statements with the same shape count as one. String and number literals
  are replaced by `?` and `IN (?, ?, ?)` lists by `(?)`, so
  `SELECT * FROM items WHERE order_id = 7` and `... = 8` are the same
  statement, as are two runs of a prepared statement.
- The statements of `async()` tasks count for the request that started them.
- The warning is logged when the request ends, with the route pattern (never
  the raw path) or the gRPC method, and the count.
- Each route and statement is logged at most once a minute, so a busy route
  with an N+1 logs one line a minute, not one per request.
- Parameters are never logged, and literals are removed from the statement
  before it is counted. Double-quoted text is kept: it names columns and
  tables in standard SQL. MySQL also accepts it as a string, so keep values
  out of double quotes, or better, in parameters.
- Off by default (0). Statements run outside a request, at boot or in
  `offload()` jobs, are not counted.

`examples/repeated` in the Cairo repository has a request that loads 12
orders one by one, half of them in `async()` tasks.

## What it costs

Off, one branch per statement. On, each statement costs a call from C
into PHP and a lookup of its shape: each thread remembers the shapes of
512 statements, so the literals are only stripped the first time. On the
PostgreSQL point-query benchmark the change was within noise (+1.0 %
and -0.2 % in the two orders). Without that cache it cost about 5 %.

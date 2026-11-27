# PostgreSQL

`pgsql:` DSNs go to PHP's own `pdo_pgsql`, on libpq, in every Cairo binary
and image. Everything it does works as under PHP-FPM, with PHP's own
behaviour and error messages: prepared statements, transactions,
`lastInsertId()`, `getColumnMeta()`, the `PDO::PGSQL_ATTR_*` attributes,
LISTEN/NOTIFY, COPY and large objects. On PHP 8.4 and newer the same
methods are on `Pdo\Pgsql` as well.

```php
$pdo = new PDO('pgsql:host=127.0.0.1;port=5432;dbname=app', 'app', 'secret');
$st = $pdo->prepare('SELECT * FROM users WHERE id = :id');
$st->execute(['id' => 7]);
```

## Waits suspend only the fiber

libpq waits for the server whenever a query, a connect, a COPY or a large
object needs its answer. Inside a request fiber Cairo parks that fiber on
the thread's own event loop (`Hook::PGSQL`) and the thread runs its other
fibers meanwhile. With one PHP thread, 50 requests running `pg_sleep(1)`
finish in about 1 second.

```php
$pdo->exec('LISTEN jobs');
// Waits up to 5 s; in a request fiber only this fiber waits.
$note = $pdo->pgsqlGetNotify(PDO::FETCH_ASSOC, 5000);
```

`pgsqlGetNotify()` with a timeout waits the same way.

## One round trip a statement

A new connection has `PDO::PGSQL_ATTR_DISABLE_PREPARES` on, unless its
options set it: `prepare()` and `execute()` then send the statement and its
parameters in one round trip, instead of three (prepare, execute,
deallocate). Placeholders still go as parameters, never in the SQL text. To
keep statements prepared on the server, ask for it:

```php
$pdo = new PDO($dsn, $user, $pass, [PDO::PGSQL_ATTR_DISABLE_PREPARES => false]);
```

On a real request that makes two queries this default measured 33% more
requests per second in fiber mode and 47% in isolated mode than Cairo 0.7's
driver.

## Deadlines and clients that leave

When the request's deadline passes, or its client goes away, in the middle
of a query, the query's wait ends at once with the context's exception
(`Cairo\Context\DeadlineExceeded` or `Cairo\Context\Canceled`), and
`Context::withTimeout()` works the same for one query. The server still
runs the query and sends its answer, so Cairo closes that connection: its
next statement fails rather than read the answer of the one that was cut.
Open a new `PDO` for what follows; a `Cairo\Pool` drops a connection whose
callback threw.

Use one `PDO` per fiber (for example through [`Cairo\Pool`](pools.md)): a
connection runs one query at a time.

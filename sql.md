# Cairo\Sql

A small typed API over Go's `database/sql`, for PostgreSQL (pgx) and MySQL or
MariaDB (go-sql-driver/mysql). The pool
lives in Go and is shared by every PHP thread: `Db::open()` with the same DSN
and options returns the same pool on each thread, so `max_open` bounds the
connections of the whole server rather than of each thread.

```php
use Cairo\Sql\Db;

$db = Db::open('postgres://app:secret@127.0.0.1/app', ['max_open' => 20]);

$users = $db->query('SELECT id, name FROM users WHERE team = $1', [$team]);   // list of rows
$user  = $db->queryRow('SELECT * FROM users WHERE id = $1', [$id]);           // a row or null
$count = $db->queryValue('SELECT count(*) FROM users');
$n     = $db->exec('UPDATE users SET seen = now() WHERE id = $1', [$id]);    // rows changed

$db->transaction(function (Cairo\Sql\Tx $tx) use ($from, $to, $amount): void {
    $tx->exec('UPDATE accounts SET balance = balance - $1 WHERE id = $2', [$amount, $from]);
    $tx->exec('UPDATE accounts SET balance = balance + $1 WHERE id = $2', [$amount, $to]);
});   // committed, or rolled back if the callback throws
```

Queries suspend only the calling fiber, and the request's deadline cancels
them. Integers, floats, booleans, text and nulls come back as PHP values;
bytea as a string, timestamps as RFC 3339 strings in UTC, and numeric, json and the
rest in PostgreSQL's text form. Pass binary parameters as
`new Cairo\Sql\Bytes($raw)`. Failures throw `Cairo\Sql\SqlException` with
`$sqlState`. A transaction left open when its fiber ends is rolled back.
`examples/sql` has more. PDO with `pgsql:` keeps working beside it.

For MySQL, open a `mysql://` URL and use `?` placeholders:

```php
$db = Db::open('mysql://app:secret@127.0.0.1:3306/app');   // ?socket=/run/mysqld/mysqld.sock for a Unix socket
$user = $db->queryRow('SELECT * FROM users WHERE id = ?', [$id]);
```

Text columns come back as strings and binary ones (BLOB, VARBINARY) as
strings too, DATETIME and TIMESTAMP as RFC 3339 in UTC, DATE as `Y-m-d`, and
DECIMAL as text. `SqlException::$sqlState` is MySQL's SQLSTATE, and
`$detail` names the MySQL error number. Other go-sql-driver/mysql parameters
(`tls`, `timeout`, `loc`, ...) go in the URL's query. Parameters are
interpolated into the query by the driver (`interpolateParams=true`), so a
query is one round trip instead of three (prepare, execute, close); set
`interpolateParams=false` in the URL for server-side prepared statements.
`examples/sql/mysql.php`
is the same example as `server.php` for MySQL. PDO MySQL keeps working too,
through the hooked streams.

## A shared pool, safely

Each statement on `$db` takes whichever connection is free and gives it back
when it ends, so nothing it leaves on that connection may reach the next
request:

- `BEGIN`, `START TRANSACTION`, `SET autocommit`, `LOCK` and `XA` on `$db`
  throw a `SqlException`. Use `$db->transaction()`, which keeps one
  connection until it commits or rolls back.
- A PostgreSQL connection that comes back in a transaction anyway (a
  multi-statement string such as `SELECT 1; BEGIN`) is closed, which rolls it
  back, instead of being reused. MySQL URLs refuse `multiStatements`.
- Other session state (`SET search_path`, temporary tables, `GET_LOCK()`,
  advisory locks) does reach the next request, as with any pool: set it inside
  a transaction (`SET LOCAL`), or avoid it.

### Waiting for a connection

```php
$db = Db::open($dsn, ['max_open' => 20, 'acquire_timeout' => 2.0]);
```

When all `max_open` connections are in use, a query waits for one on its
fiber. Without `acquire_timeout` it waits until the request ends (its
deadline, or the client going away). With it, the query throws a
`Cairo\PoolTimeout` after that many seconds: turn it into a 503. `stats()`
returns `wait_count` and `wait_time` to size the pool. `max_lifetime` and
`max_idle_time` (seconds) retire old connections; set them below the
server's own idle timeout (`wait_timeout` on MySQL).

`examples/sql/hardening.php` shows each of these on PostgreSQL and MySQL.

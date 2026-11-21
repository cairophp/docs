# Connection pools

Each fiber needs its own connection. `Cairo\Pool` keeps a pool per PHP thread
(build it in `server.php`, which every thread runs):

```php
$db = new Cairo\Pool(fn () => new PDO($dsn, $user, $pass), max: 10);

$pdo = $db->get();                                  // this fiber's, returned when it ends
$db->with(fn (PDO $pdo) => $pdo->query('SELECT 1')); // borrowed for the callback only
```

When all connections are in use, `get()` suspends the fiber until one comes
back. Using one connection from two fibers at once throws instead of
corrupting the protocol. A connection is dropped instead of given back when
the request was cancelled or past its deadline while holding it (a wait it was
in may have cut a reply short), and, with `with()`, when the callback throws.
After a connection error with `get()`, call `discard()`.

## Waiting for a connection

```php
$db = new Cairo\Pool($factory, max: 10, acquireTimeout: 2.0);
```

- Without `acquireTimeout`, a request waits until a connection comes back.
  A request past its deadline (`Middleware::timeout()`) is skipped then, and
  its `get()` throws a `Cairo\Context\ContextException`.
- With `acquireTimeout`, `get()` throws a `Cairo\PoolTimeout` after that many
  seconds, and a request whose client went away stops waiting at once. The
  PHP thread keeps a timer for this wait, which costs a little on a pool that
  is always full.

Turn a `PoolTimeout` into a 503: it means the pool is too small for the
load, or a query is slow. `stats()` returns `open`, `idle`, `waiting` and
`max`.

## PostgreSQL: one pool for all threads

Cairo's own pgsql driver can share server connections between threads. Add
`cairo_pool=N` to the DSN:

```php
$db = new Cairo\Pool(fn () => new PDO("pgsql:host=db;dbname=app;cairo_pool=40", $user, $pass), max: 40);
```

Each `PDO` is then a handle with no server connection of its own. On its
first statement in a request it borrows one of N connections shared by every
thread, and gives it back when the request ends, so a busy thread uses
connections an idle thread does not need. PDO objects with the same DSN and
user share one pool, so give them the same `cairo_pool`.

- A transaction keeps its connection until it ends. One left open when the
  request ends is rolled back before the connection is reused.
- Session settings (`SET`, temporary tables) can reach the next request on
  that connection, as with any pool: reset them, or use `SET LOCAL` inside a
  transaction.
- LISTEN/NOTIFY needs a connection of its own: use a DSN without
  `cairo_pool` for it.
- A request waits for a free connection only on its fiber, and stops waiting
  at its deadline.

## What the next request gets

A connection is reset before another fiber uses it:

- By default, a PDO transaction a request left open is rolled back.
- `reset:` replaces that with your own check, for example
  `reset: fn (PDO $pdo) => $pdo->exec('DISCARD ALL')` on PostgreSQL when
  requests change session settings. It runs on every return, so keep it
  cheap.
- A connection whose reset throws is dropped, and the pool opens a new one.

## Retiring connections

```php
$db = new Cairo\Pool($factory, max: 10, maxLifetime: 1800, maxIdleTime: 300);
```

`maxLifetime` and `maxIdleTime` are in seconds (0: no limit). Set them below
the server's own idle timeout (`wait_timeout` on MySQL) and any firewall's,
so a request never gets a connection the other side has already closed.

`examples/pool` has a runnable server with each of these.

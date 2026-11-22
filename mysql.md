# MySQL and MariaDB

Cairo uses PHP's own drivers for MySQL: PDO MySQL and mysqli, both on
mysqlnd. Existing code needs no changes. Inside a request fiber a query
suspends only its fiber (`Hook::SOCKETS`, see [Runtime hooks](runtime-hooks.md)):
the PHP thread watches the connection's socket and runs other requests until
the reply arrives, and the request's deadline ends the wait.

```php
$db = new Cairo\Pool(fn () => new PDO('mysql:host=127.0.0.1;dbname=app', $user, $pass), max: 10);

$http->get('/users/{id}', function (Request $req) use ($db): Response {
    $user = $db->with(function (PDO $pdo) use ($req): array|false {
        $st = $pdo->prepare('SELECT id, name FROM users WHERE id = ?');
        $st->execute([$req->param('id')]);
        return $st->fetch(PDO::FETCH_ASSOC);
    });
    return Response::json($user);
});
```

A connection runs one query at a time, so each fiber needs its own: keep them
in a [connection pool](pools.md).

## Recommended: turn off mysqlnd's statistics

Add this line to the php.ini that Cairo loads (`cairo serve --php-ini FILE`,
see [Building](building.md) for how Cairo finds its php.ini):

```ini
mysqlnd.collect_statistics = 0
```

**What it turns off.** While it works, mysqlnd counts what it does in about 160
counters: bytes sent, packets received, rows fetched and so on. Only
`mysqli_get_client_stats()`, `mysqli_get_connection_stats()` and the mysqlnd
section of `phpinfo()` read them. PHP has the counters on by default, and
Cairo leaves PHP's default as it is.

**Why it costs more on Cairo than on PHP-FPM.** The counters are one table
for the whole process. Cairo runs PHP's thread-safe build, where every
increment of a counter takes a lock on that table. With several PHP threads
running queries at the same time, the threads queue on the lock, and a thread
that has to wait for it sleeps in the kernel. The more rows a query returns,
the more often it takes the lock. PHP-FPM does not pay this: each of its
processes has its own counters and needs no lock.

**What it gives.** Measured on 2 CPUs with 4 PHP threads and 64 connections:

| Request | Statistics on | Statistics off | Change |
|---|---|---|---|
| Two queries (one row, then 20 rows) and a 1.5 KB JSON answer | 12,084 req/s | 15,360 req/s | +27% |
| One query that returns one row | 29,554 req/s | 32,052 req/s | +8.7% |

Each row is its own run, with on and off taking turns, so compare within a
row. With the statistics on, the first request made about 20 system calls to
sleep on the lock and be woken; with them off, fewer than one.

**What you lose.** The three readers above report zeros. Queries, results,
errors, transactions and the MySQL server's own statistics (`SHOW STATUS`,
the slow query log, `performance_schema`) are not affected. If a monitoring
tool of yours reads the client statistics, leave the setting on.

`mysqlnd.collect_memory_statistics` is a separate setting and is already off
by default.

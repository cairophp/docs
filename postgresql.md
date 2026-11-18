# PostgreSQL

Cairo has its own PDO driver for `pgsql:` DSNs, written in C on the PDO side
and backed by Go's pgx (`pgconn`) on the other, so it needs no libpq. Inside a
request fiber each query runs on the fiber's goroutine (`Hook::PGSQL`): the
fiber suspends, and the request's deadline cancels the query. With one PHP
thread, 50 requests running `pg_sleep(1)` finish in about 1 second (50
seconds with the hook off).

```php
$pdo = new PDO('pgsql:host=127.0.0.1;port=5432;dbname=app', 'app', 'secret');
$st = $pdo->prepare('SELECT * FROM users WHERE id = :id');
$st->execute(['id' => 7]);
```

Prepared statements, `?` and `:name` placeholders, transactions,
`lastInsertId()`, `quote()`, `getColumnMeta()` and the error modes work as
with pdo_pgsql; `int2/int4/int8` and `bool` columns come back as PHP ints and
bools, and `bytea` as a read-only stream, as with pdo_pgsql. Results are read in
full, like libpq's `PQexec`. Use one `PDO` per fiber (for example through
`Cairo\Pool`): a connection runs one query at a time. The driver registers
only when PHP has no pdo_pgsql of its own; the `PGSQL_ATTR_*` attributes
are not provided.

LISTEN/NOTIFY, COPY and large objects work through the same methods as pdo_pgsql:

```php
$pdo->exec('LISTEN jobs');
// Waits up to 5 s; in a request fiber only this fiber waits.
$note = $pdo->pgsqlGetNotify(PDO::FETCH_ASSOC, 5000); // ['message' => 'jobs', 'pid' => ..., 'payload' => ...] or false
$pid = $pdo->pgsqlGetPid();

$pdo->pgsqlCopyFromArray('items', ["1\tfirst", "2\tsecond"]);
$pdo->pgsqlCopyFromFile('items', '/tmp/items.tsv', "\t", '\\N', 'id, name');
$rows = $pdo->pgsqlCopyToArray('items');      // one line per row, with "\n"
$pdo->pgsqlCopyToFile('items', '/tmp/out.tsv');

$pdo->beginTransaction();                     // large objects need a transaction
$oid = $pdo->pgsqlLOBCreate();                // the new object's OID, as a string
$lob = $pdo->pgsqlLOBOpen($oid, 'w');         // a PHP stream: fwrite, fread, fseek, ftell
fwrite($lob, $bytes);
fclose($lob);
$pdo->commit();
$pdo->pgsqlLOBUnlink($oid);
```

Notifications that arrive while the connection runs other queries are kept
until `pgsqlGetNotify()` takes them. COPY data is held in memory in one
piece, both ways. Each large object read, write or seek is one statement on
the server's `lo_*` functions, run by Go, so in a fiber only the fiber waits.

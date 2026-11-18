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

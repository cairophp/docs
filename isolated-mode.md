# Isolated mode

Apps that are a set of scripts, such as WordPress, need a fresh PHP request
for every request instead: see [Classic mode](classic.md).

Apps that keep request state in globals or singletons (many Laravel and
Symfony apps, most legacy code) can run with one request per PHP thread at a
time:

```php
$app->concurrency('isolated')
    ->resetAfterRequest($container->get(CurrentUser::class), fn () => Cache::flushLocal());

$http->get('/legacy', function (): void {     // classic PHP works
    header('Content-Type: application/json');
    echo json_encode(['id' => $_GET['id'], 'ip' => $_SERVER['REMOTE_ADDR']]);
});
```

In isolated mode Cairo fills `$_GET`, `$_POST` (url-encoded and multipart
forms), `$_FILES`, `$_COOKIE`, `$_SERVER` and `$_REQUEST`; `$_SERVER` also
keeps what the app put there as its thread started (Symfony's runtime and
Dotenv put the app's settings there), under the request's own keys; the
process's environment is in `getenv()` and `$_ENV` (a `putenv()` is the
request's own and is gone when it ends; what `server.php` set as the thread
started is where every request begins: see [Classic mode](classic.md)); a handler that returns nothing answers with what it
echoed, its `header()` calls and `http_response_code()`. `flush()` sends what
was echoed so far, and `headers_send(103)` and `fastcgi_finish_request()`
work as under other PHP servers: see [Streamed answers](streaming.md). After each request it
clears the superglobals and calls `reset()` on everything given to
`resetAfterRequest()` (any object with a `reset()` method, such as
`Cairo\Resettable` or Symfony's `ResetInterface`, or a callable). Requests that
arrive while every thread is busy wait in one first-in, first-out queue, and
go to the next thread that is free, so a slow request never holds up the ones
behind it while another thread is idle.

<!-- illustration: mode-isolated -->

## How many threads

A thread runs one request at a time, so `threads()` (or Octane's
`--workers`) is how many requests run at once. Threads that wait for a
database or an HTTP call use no CPU, so an app whose requests mostly wait
wants many of them. An app whose requests mostly compute (a framework's own
work counts) does not: under load a thread that answers takes the next
request at once, every thread stays runnable, and the system shares the CPUs
among them in turns. A request paused halfway then waits for the other
threads' turns, so the slowest requests get slower while the typical one
does not.

Laravel's hello through Octane on 2 CPUs, under load:

| Threads | Requests/s | p50 | p99 |
|---------|------------|-----|-----|
| 8 | 2,025 | 28 ms | 53 ms |
| 40 | 2,004 | 23 ms | 132 ms |

Start with about 4 threads per CPU, raise it while requests wait more than
they compute, and watch the p99 (the [metrics](observability.md) histogram has it) as
you do.

Uploads are parsed by Go into temporary files that are removed after the
request. `move_uploaded_file()` and `is_uploaded_file()` accept them in both
modes; in fiber mode use `$req->form()` and `$req->file('photo')`, which gives a
`Cairo\Http\UploadedFile` with `name`, `type`, `size`, `path`, `contents()` and
`moveTo()`.

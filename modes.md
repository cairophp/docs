# Concurrency in each mode

Cairo runs PHP in five ways. In every one of them a request (or a script)
can run work at the same time with the [concurrency API](concurrency.md):
`Cairo\async()`, `await()` and `all()`, channels and `select()`,
[contexts with deadlines](context.md) and `offload()`. What changes from one
mode to the next is how requests share a PHP thread.

| Mode | How it starts | Requests on a thread at once | Inside one request | Made for |
|---|---|---|---|---|
| [Fibers](modes.md#fiber-mode) (the default) | `cairo serve server.php` | many, a fiber each | `async()` tasks run in fibers | apps that keep no request state in globals or statics |
| [Isolated](modes.md#isolated-mode) | `->concurrency('isolated')` | one | the same | Laravel through Octane, Symfony, apps with globals |
| [Classic](modes.md#classic-mode) | `->concurrency('classic')` and `scripts()` | one, in a new PHP request | the same; the script itself runs on the thread's stack | WordPress and other script apps |
| [No declaration](modes.md#no-declaration) | `cairo serve public/` | one, PHP's own SAPI request | the same as classic | a folder or a front controller, as under PHP-FPM |
| [`cairo php`](modes.md#cairo-php) | `cairo php script.php` | the script is the thread's one request | the script is the first fiber | commands, workers, scripts |

In every mode, a wait that Cairo hooks (`sleep()`, PDO MySQL and
PostgreSQL, curl, streams, the `Cairo\` clients) suspends only the fiber
that waits. Fiber mode uses that between requests; every mode uses it
between the tasks of one request.

## Fiber mode

One thread holds many requests. Each starts in a fiber of its own, and
when its handler waits, only that fiber suspends: the thread runs the next
request meanwhile. This is why one PHP thread can hold thousands of
requests that wait on databases and APIs. Code must keep its request state
on the `Request`, in [Context values](context-values.md) or in
[request-local statics](request-local.md), because other requests run on
the same thread.

<!-- illustration: mode-fibers -->

## Isolated mode

A thread runs one request at a time, and the requests that find every
thread busy wait in Go, in one first-in, first-out queue. The superglobals
are filled, `echo` and `header()` are the answer, and after each request
Cairo clears them and runs your resets. Inside a request, `async()` tasks
still run in fibers of that request, so their waits overlap. See
[Isolated mode](isolated-mode.md).

<!-- illustration: mode-isolated -->

## Classic mode

Every request is a new PHP request, as under PHP-FPM: the script loads the
app's files, and its globals, functions and constants are its own. The
script runs on its thread's own stack, not in a fiber, so its own waits
hold the thread as they would hold a PHP-FPM worker. Its `async()` tasks run
in fibers of the request, and `await()` lets their waits overlap. See
[Classic mode](classic.md).

<!-- illustration: mode-classic -->

## No declaration

A folder, or a PHP file that declares no `Cairo\App`, is served as nginx and
PHP-FPM serve it: `cairo serve public/`. Each request is PHP's own SAPI
request, with no Cairo PHP code around the script, and Cairo's concurrency
functions are there from its first line. See
[Serving with no declaration](classic.md#serving-with-no-declaration).

<!-- illustration: mode-plain -->

## `cairo php`

The binary is also PHP's command line. A script is the one request of one
PHP thread, and it runs as the first fiber of the scheduler, so its
`async()` tasks overlap their waits. While the script is the only fiber, a
wait uses the thread as under `php`, so a command that starts no task pays
nothing. See [PHP command line](cli.md).

<!-- illustration: mode-cli -->

## The same checks in every mode

This function runs as a route in fiber, isolated and classic mode, as a
script of a folder served with no declaration, and with `cairo php`:

```php
use Cairo\{Channel, Context};
use function Cairo\{async, await, all, sleep, select, offload};

$tasks = [async(fn () => sleep(0.2)), async(fn () => sleep(0.2)), async(fn () => sleep(0.2))];
foreach ($tasks as $task) { await($task); }                        // 200 ms in all

await(all([async(fn () => \usleep(200000)), async(fn () => \usleep(200000))]));

[$key] = select(['never' => new Channel()], 0.05);                 // null after 50 ms

try {
    Context::current()->withTimeout(0.05)->run(fn () => sleep(1));
} catch (Context\DeadlineExceeded $e) {
    // after 50 ms
}

$hash = offload('hash', 'sha256', 'cairo');
```

In each of the five, on Cairo 0.8.1 with PHP 8.6:

| Check | Result |
|---|---|
| three `Cairo\sleep(0.2)` in `async()` tasks | 200 ms |
| two `usleep(200000)` under `all()` | 200 ms |
| two PDO MySQL `SELECT SLEEP(0.2)`, a connection each | 202 ms |
| a `Channel` between a task and its reader | 1, 2, 3 |
| `select()` on a channel nobody sends to, with a 0.05 s timeout | `null` after 50 ms |
| `withTimeout(0.05)` around `sleep(1)` | `Context\DeadlineExceeded` |
| `offload('hash', ...)` | the hash; in place for `cairo php`, whose one thread has no offload pool |

# Thread supervision

A fatal error (such as running out of `memory_limit`) ends the whole PHP
thread, not only the request that caused it. Cairo answers the requests that
thread was running with 500 (gRPC `INTERNAL`), logs the PHP error, and starts
a fresh thread in its place; requests still waiting for that thread are served
by the new one. A thread that keeps dying right after it starts stops the
server instead of restarting forever.

To keep slow leaks in check, a request thread can be replaced on purpose:

```php
$app->maxRequests(10_000)   // after this many requests
    ->maxMemory('256M');    // or once memory_get_usage() reaches this, checked after each request
```

Cairo starts the replacement first. The old thread keeps serving until the new
one has run `server.php`, which is where a framework boots, so no request
waits for that boot. Then new requests go to the new thread, and the old one
finishes the requests it holds before it exits. No request fails. For the
length of the boot the old thread serves past `maxRequests()`, and both
threads hold their memory.

`$app->maxInFlight(100)` caps the requests each request thread holds at once.
Requests over the cap wait in Go until one finishes, or until their own
deadline. A waiting request costs a goroutine, not PHP memory.
`examples/supervise` shows both.

## When opcache has to restart

opcache keeps the compiled code of every PHP thread in one shared memory. It
empties that memory and starts over when it is full and part of it is stale
(the code of files that have changed on disk since), or when the app calls
`opcache_reset()`. PHP can only do that safely when nothing runs code from the
cache, which in a server of threads means: in a new process.

So when opcache asks for its restart, Cairo starts no PHP thread any more.
The threads that run serve on. The next time a thread would start (one is
recycled, or one has died), the server stops as it does on SIGTERM, with the
requests in flight finished, and starts anew in place, under the same process
id:

```
level=WARN msg="restarting in place" because="no PHP thread can start until the process has started anew: opcache's memory is full (opcache.memory_consumption)"
```

Until the new process listens, connections are refused: for as long as your
app takes to start, after the requests in flight. To make it rare:

- Give opcache room for your code: `opcache.memory_consumption` (128 MB by
  default) and `opcache.max_accelerated_files`. The log names the one that
  ran out.
- Do not call `opcache_reset()` in a deploy, as is done for PHP-FPM. Restart
  the server instead: a new process has an empty cache.
- Restart the server when you deploy. Threads that are recycled later read
  the files as they are on disk then, and each changed file leaves its old
  code behind in the cache.

Before this, such a restart ended the process with `zend_mm_heap corrupted`.

## Stopping the server

On SIGINT or SIGTERM Cairo stops accepting connections and waits for the
requests in flight, for `--grace` at most (30 s by default). With
`--drain 5s` it first keeps serving for that long while its
[readiness probe](observability.md) answers 503, so a load balancer stops
sending before connections close. Then each PHP
thread finishes what it still holds before it ends: a request whose client
has left runs to its end, `finally` blocks included, and a fiber that still
waits for an answer from Go gets it first. Once the grace time is over, the
server exits with whatever is left.

A handler that calls `exit()` ends its whole thread, as a fatal error does:
the requests that thread was running get 500, and Cairo starts a fresh
thread.

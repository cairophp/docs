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

## Stopping the server

On SIGINT or SIGTERM Cairo stops accepting connections and waits for the
requests in flight, for `--grace` at most (30 s by default). Then each PHP
thread finishes what it still holds before it ends: a request whose client
has left runs to its end, `finally` blocks included, and a fiber that still
waits for an answer from Go gets it first. Once the grace time is over, the
server exits with whatever is left.

A handler that calls `exit()` ends its whole thread, as a fatal error does:
the requests that thread was running get 500, and Cairo starts a fresh
thread.

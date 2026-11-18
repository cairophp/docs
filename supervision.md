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

Cairo starts the replacement first and sends new requests to it, then lets the
old thread finish the requests it holds before it exits, so no request fails.

`$app->maxInFlight(100)` caps the requests each request thread holds at once.
Requests over the cap wait in Go until one finishes, or until their own
deadline. A waiting request costs a goroutine, not PHP memory.
`examples/supervise` shows both.

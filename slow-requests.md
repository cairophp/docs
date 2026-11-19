# Slow request log

Every wait of a request goes through Go: queries, HTTP calls, sockets,
sleeps, channel waits and offload jobs. So Go can log where a slow request
spent its time, with no code in the app:

```php
$app->slowRequests(0.5);   // log requests that take longer than 0.5 s
```

```
level=WARN msg="slow request" route="GET /orders/{id}" ms=1240 php_ms=40 sql="38 in 310ms" http="2 in 890ms"
```

- `route` is the route's method and pattern (never the raw path), or the
  full gRPC method.
- `ms` is the whole request. `php_ms` is the time when none of the request's
  fibers was waiting in Go: PHP running, or the request queued behind other
  requests on its thread. If it is high and the CPU is idle, look for a
  blocking call with [the blocking detector](blocking.md).
- Each kind of wait that happened is listed with its count and total time:
  - `sql`: PDO pgsql and `Cairo\Sql`.
  - `http`: `Cairo\Http\Client` and curl.
  - `socket`: other hooked sockets, such as PDO MySQL, Redis and streams.
  - `connect`: DNS, connect and TLS handshakes.
  - `sleep`.
  - `wait`: channels, `select()`, and `Cairo\Pool` with `acquireTimeout`.
  - `offload`.
  - `grpc`: the gRPC client.
- Waits of `async()` tasks run side by side, so the kinds can add up to
  more than `ms`.
- A request that ends at its deadline, or because the client went away, is
  logged with `ended=deadline_exceeded` or `ended=canceled`.

Two waits happen in PHP rather than in Go, so they count as `php_ms`: socket
waits shorter than about 1 ms, and a `Cairo\Pool` wait without
`acquireTimeout`. Nothing from the request, such as parameters,
headers or query text, is logged.

The log costs nothing measurable. It is off by default (0), and when on it
adds two clock reads per wait. `examples/slow` has a request with an HTTP
call, waits in `async()` tasks and CPU work.

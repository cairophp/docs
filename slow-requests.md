# Slow request log

Every wait of a request goes through Cairo: queries, HTTP calls, sockets,
sleeps, channel waits and offload jobs. So Cairo can log where a slow request
spent its time, with no code in the app:

```php
$app->slowRequests(0.5);   // log requests that take longer than 0.5 s
```

```
level=WARN msg="slow request" route="GET /orders/{id}" ms=1240 php_ms=40 longest_run_ms=12 sql="38 in 310ms" http="2 in 890ms"
```

- `route` is the route's method and pattern (never the raw path), or the
  full gRPC method.
- `ms` is the whole request. `php_ms` is the time when none of the request's
  fibers was waiting: PHP running, or the request queued behind other
  requests on its thread. If it is high and the CPU is idle, look for a
  blocking call with [the blocking detector](blocking.md).
- `longest_run_ms` is the longest stretch of PHP the request ran without
  pausing. Every other request on its thread waited for that long. A
  high value means CPU work that belongs in `offload()`, or a blocking call.
- Each kind of wait that happened is listed with its count and total time:
  - `sql`: PDO pgsql.
  - `http`: curl.
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

Two waits are not counted, so they show as `php_ms`: in isolated mode, a
socket wait shorter than about 1 ms, and a `Cairo\Pool` wait without
`acquireTimeout`. Nothing from the request, such as parameters,
headers or query text, is logged.

It is off by default (0). Off, it costs one nil check per wait; on, two
clock reads per wait. Neither shows in the benchmarks: plain-text and
PostgreSQL requests per second stayed within 2% of the build without it,
less than the run-to-run noise. `examples/slow` has a request with an HTTP
call, waits in `async()` tasks and CPU work.

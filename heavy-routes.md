# Heavy routes

A PHP thread runs many requests at once, one fiber each, but only one of
them runs PHP at a time. While a request computes without waiting on I/O,
every other request on its thread waits for it. Cairo can name the routes
that do this, measured with no code in the app:

```php
$app->heavyRoutes(0.05);   // warn about stretches of PHP longer than 50 ms
```

```
level=WARN msg="heavy route: move its CPU work to offload()" route="POST /report" longest_run_ms=212
```

- `route` is the route's method and pattern (never the raw path), or the
  full gRPC method.
- `longest_run_ms` is the longest stretch of PHP that one request ran
  without pausing. Every wait through Cairo pauses it: queries, HTTP
  calls, sockets, `sleep()`, channels and `offload()`.
- Each route is logged at most once a minute, however often it runs.
- The fix is usually to move the work into `Cairo\offload()`. It runs on an
  offload thread, and the request thread serves other requests meanwhile.
  Splitting the work with waits in between also helps, since each stretch is
  then short.
- A stretch that is long because of a blocking call Cairo does not hook
  looks the same. [The blocking detector](blocking.md) shows where it
  blocked, with a stack.
- Isolated mode is not reported, because blocking calls are expected
  there and would count as PHP.

It is off by default (0). It uses the same timing as the
[slow request log](slow-requests.md): off, one nil check per wait; on, two
clock reads per wait. Neither shows in the benchmarks: plain-text and
PostgreSQL requests per second stayed within the run-to-run noise. `examples/heavy` has a heavy route, the same work
split by waits, and the same work in `offload()`. Only the first is logged.

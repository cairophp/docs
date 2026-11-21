# Amp and Revolt

Libraries built on [Revolt](https://revolt.run) (Amp v3, and ReactPHP through
its fiber adapters) run on Cairo's scheduler instead of a second event loop:

```php
require __DIR__ . '/vendor/autoload.php';

Cairo\Revolt\Driver::install();   // once, in server.php
```

`Amp\delay()`, `Amp\async()`, futures, cancellations and Amp's sockets and
HTTP client then wait like any other Cairo call, so one PHP thread
serves many such requests at once. In the example, 20 `amphp/http-client`
requests to a 1s endpoint take about 1s on one thread. Each Revolt callback
runs in an `async()` task: `defer()` and `queue()` as soon as the current
fiber yields, timers on the thread's timers, and `onReadable()`/`onWritable()`
when the thread's epoll sees the socket ready. A `Suspension` parks its fiber
on the thread.

Some things differ from Revolt's own drivers:

- A callback belongs to the request that scheduled it, and ends with it.
- `queue()` and `defer()` run in the order they were scheduled.
- `onSignal()` throws `UnsupportedFeatureException`, because Go handles signals.
- An exception from a callback with no error handler is logged, not thrown out of `run()`.

See `examples/revolt`.

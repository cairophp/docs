# Finding blocking code

Fibers share their PHP thread, so a request that runs a long CPU loop or a
blocking C call Cairo does not hook stalls every other request on that thread.
In development, turn on the detector:

```php
$app->detectBlocking(0.1);   // seconds a request may hold its thread without yielding
```

Go watches each request thread. When one stays in PHP past the threshold, the
running fiber logs once, at its next safe point, how long it held the thread
and where it was:

```
cairo: blocking: request 5 kept its PHP thread busy for 109ms; other requests on the thread waited. At:
  /app/routes/report.php:30 in {closure}()
```

Calls Cairo hooks (`sleep()`, `usleep()`, curl, sockets, PDO pgsql and so on)
yield, so they are never reported. The check costs a timer tick in Go and
nothing in PHP until it fires. Isolated mode, which runs one request per thread,
does not report. `examples/blocking` has a loop, a long `password_hash()` and
two calls that yield.

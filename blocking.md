# Finding blocking code

Fibers share their PHP thread, so a request that runs a long CPU loop or a
blocking C call Cairo does not hook stalls every other request on that thread.
In development, turn on the detector:

```php
$app->detectBlocking(0.1);   // seconds a request may hold its thread without yielding
```

Go watches each request thread. When a fiber keeps its thread past the
threshold, it logs once, at its next safe point, how long it held the thread
and where it was:

```
cairo: blocking: request 5 kept its PHP thread busy for 109ms; other requests on the thread waited. At:
  /app/routes/report.php:30 in {closure}()
```

Calls Cairo hooks (`sleep()`, `usleep()`, curl, sockets, PDO pgsql and so on)
yield, so they are never reported. Neither are fibers that become ready at
the same moment and each run for a short time, such as ten tasks whose sleeps
end together: the thread runs them one after the other, and each is counted
from where it began. The check costs a timer tick in Go and nothing in PHP
until it fires. Isolated mode, which runs one request per thread, does not
report. `examples/blocking` has a loop, a long `password_hash()` and four
routes that yield.

# Runtime hooks

Cairo swaps the handlers of some blocking PHP functions so that, inside a
request fiber, they suspend only the fiber, and existing code needs no
changes. Sleeps and socket waits stay on the PHP thread, which keeps their
timers and watches the sockets itself; DNS, connects, TLS and PostgreSQL
queries run in Go. Outside request fibers (the declare phase, offload
threads, fibers your own code creates) the original functions run.

| Hook | Functions | Notes |
|---|---|---|
| `Hook::SLEEP` | `sleep()`, `usleep()`, `time_nanosleep()` | |
| `Hook::SOCKETS` | reads and writes on `tcp://` and `unix://` streams: mysqlnd (PDO MySQL, mysqli), Predis, phpredis, `fsockopen()`, `stream_socket_client()` | each PHP thread watches the sockets of its fibers in an epoll of its own; in isolated mode, where a thread has nothing else to run, it first polls the socket itself for up to 1 ms |
| `Hook::CONNECT` | connects on those streams, DNS included, and TLS handshakes | Go's dialer; falls back to PHP when a `bindto` option is set |
| `Hook::DNS` | `gethostbyname()`, `gethostbynamel()` | Go's resolver |
| `Hook::CURL` | `curl_exec()`, `curl_multi_select()` (Guzzle's multi handler) | libcurl still does the transfer; only its socket waits become waits of the fiber, so `curl_getinfo()`, `curl_error()` and callbacks are unchanged. Connections are kept alive per handle, and a new handle takes over those of a closed one on the same thread. `curl_multi_select()` sees descriptors above 1023 only with libcurl 8.8 or later (the static binary has it); with older libcurl it polls those every 100 ms |
| `Hook::PGSQL` | PDO `pgsql:` queries | libpq's waits; see [PostgreSQL](postgresql.md) |

```php
$app->hooks(Hook::ALL);    // the default; Hook::NONE turns them off
```

A hooked call honours the request's deadline like `Cairo\sleep()` does.
Socket waits go through the epoll of their PHP thread, so a thousand waiting
queries hold no OS threads and no goroutines. With one PHP thread, 50 PDO queries running
`SELECT SLEEP(1)` finish in about 1 second (20 take 20 seconds with
`Hook::NONE`).

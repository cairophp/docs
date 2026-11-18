# Runtime hooks

Cairo swaps the handlers of some blocking PHP functions so that, inside a
request fiber, they suspend the fiber while its goroutine waits, and existing
code needs no changes. Outside request fibers (the declare phase, offload
threads, fibers your own code creates) the original functions run.

| Hook | Functions | Notes |
|---|---|---|
| `Hook::SLEEP` | `sleep()`, `usleep()`, `time_nanosleep()` | |
| `Hook::SOCKETS` | reads and writes on `tcp://` and `unix://` streams: mysqlnd (PDO MySQL, mysqli), Predis, phpredis, `fsockopen()`, `stream_socket_client()` | waits go through one Go epoll loop; a thread with nothing else to run first polls the socket itself for up to 1 ms |
| `Hook::CONNECT` | connects on those streams, DNS included, and TLS handshakes | Go's dialer; falls back to PHP when a `bindto` option is set |
| `Hook::DNS` | `gethostbyname()`, `gethostbynamel()` | Go's resolver |
| `Hook::CURL` | `curl_exec()`, `curl_multi_select()` (Guzzle's multi handler) | libcurl still does the transfer; only its socket waits move to Go, so `curl_getinfo()`, `curl_error()` and callbacks are unchanged. Connections are kept alive per handle, and a new handle takes over those of a closed one on the same thread. `curl_multi_select()` sees descriptors above 1023 only with libcurl 8.8 or later (the static binary has it); with older libcurl it polls those every 100 ms |
| `Hook::PGSQL` | PDO `pgsql:` queries | Cairo's own driver; see PostgreSQL below |

```php
$app->hooks(Hook::ALL);    // the default; Hook::NONE turns them off
```

A hooked call honours the request's deadline like `Cairo\sleep()` does.
Socket waits go through one Go epoll loop, so a thousand waiting queries do not
hold a thousand OS threads. With one PHP thread, 50 PDO queries running
`SELECT SLEEP(1)` finish in about 1 second (20 take 20 seconds with
`Hook::NONE`).

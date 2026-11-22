# Middleware

Middleware is declared in `server.php` and runs in Go, before a request reaches
PHP, so a rejected request costs PHP nothing:

```php
use Cairo\Middleware;

$http->use(Middleware::requestId())                         // X-Request-Id, passed to PHP and echoed back
     ->use(Middleware::accessLog())
     ->use(Middleware::maxBody(1 << 20))                    // 413 above 1 MB
     ->use(Middleware::timeout(30));                        // a deadline for every request

$grpc->use(Middleware::requestId())->use(Middleware::timeout(30));
```

They run in the order declared; gRPC servers take `requestId()`,
`accessLog()` and `timeout()` (the earlier of it and the client's deadline
wins).

Without `maxBody()` a request body may be up to 32 MiB. A request that
declares more in its `Content-Length` gets 413 before any of its body is
read.

CORS, rate limits and compression are not Cairo's job: set them in the
reverse proxy in front of it or in your framework.

## What they cost

Measured on a request with a browser's headers, two MySQL queries and a
1.5 KB JSON answer (2 CPUs, 4 PHP threads, 64 connections; about 100 µs of
CPU per request):

| Middleware | CPU per request | Requests per second |
|---|---|---|
| `accessLog()` | about 6 µs: one log line is formatted and written | about 6% fewer |
| `timeout()` | about 2.6 µs: a deadline and a timer | too little for the measurement to show |
| `requestId()` | about 1.8 µs: an id, and a header on both sides | too little for the measurement to show |
| All three | about 10.6 µs | about 13% fewer |

On a request that costs more, such as a framework's, the same work is a
smaller share. An access log written by the reverse proxy in front of Cairo
costs Cairo nothing.

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

CORS, rate limits and compression are not Cairo's job: set them in the
reverse proxy in front of it or in your framework.

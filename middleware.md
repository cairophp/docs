# Middleware

Middleware is declared in `server.php` and runs in Go, before a request reaches
PHP, so a rejected or preflight request costs PHP nothing:

```php
use Cairo\Middleware;

$http->use(Middleware::requestId())                         // X-Request-Id, passed to PHP and echoed back
     ->use(Middleware::accessLog())
     ->use(Middleware::cors(origins: ['https://app.example'], credentials: true))
     ->use(Middleware::rateLimit(perSecond: 50, burst: 100)) // 429 + Retry-After, per client IP
     ->use(Middleware::maxBody(1 << 20))                    // 413 above 1 MB
     ->use(Middleware::timeout(30))                         // a deadline for every request
     ->use(Middleware::gzip());                             // responses of 1 KB or more

$grpc->use(Middleware::requestId())->use(Middleware::rateLimit(perSecond: 100));  // RESOURCE_EXHAUSTED
```

They run in the order declared; gRPC servers take `requestId()`,
`accessLog()`, `rateLimit()` and `timeout()` (the earlier of it and the
client's deadline wins).

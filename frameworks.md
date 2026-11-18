# Frameworks: PSR-15, Symfony and Laravel

Route handlers and `$http->fallback()` also accept framework objects:

```php
$http->fallback($psr15Handler);   // Psr\Http\Server\RequestHandlerInterface (Slim, Mezzio, ...)
$http->fallback($symfonyKernel);  // Symfony\Component\HttpKernel\HttpKernelInterface
$http->fallback($laravel->make(Illuminate\Contracts\Http\Kernel::class));
$http->post('/webhooks/{source}', new WebhookHandler());   // PSR-15 on one route
```

`fallback()` takes every request that no route or static path matches, with
any method. PSR-15 handlers get a PSR-7 request built with nyholm/psr7 or
guzzlehttp/psr7, whichever is installed. It carries headers, query, cookies,
the parsed form, uploaded files, and route parameters as attributes. Symfony
and Laravel kernels get an HttpFoundation request, and `terminate()` runs
after the response is sent. Streamed responses work too. The request's
`Cairo\Context` is the `cairo.context` attribute. `Cairo\Http\Adapter` does the
conversions by hand: `psr15()`, `symfony()`, `toPsr7()`, `fromPsr7()`,
`toSymfony()` and `fromSymfony()`.

Most framework apps keep request state in services and globals, so run them
with `->concurrency('isolated')` until they are known to be fiber-safe. See
`examples/frameworks`.

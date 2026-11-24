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
after the response is sent and may use the database as a handler does.
Streamed responses (`StreamedResponse`, Laravel's `response()->stream()`
and `eventStream()`) are sent while their callback writes them, and file
responses are sent in pieces, or by Go once the app trusts `X-Sendfile`:
see [Streamed answers](streaming.md). The request's
`Cairo\Context` is the `cairo.context` attribute. `Cairo\Http\Adapter` does the
conversions by hand: `psr15()`, `symfony()`, `toPsr7()`, `fromPsr7()`,
`toSymfony()` and `fromSymfony()`.

Most framework apps keep request state in services and globals, so run them
with `->concurrency('isolated')` until they are known to be fiber-safe. See
`examples/frameworks`.

## The document root

`$http->publicDir($dir)` serves the files under `$dir` at their own paths, the
way nginx or Caddy serves a document root, and sends every other request to
the routes and `fallback()`:

```php
$http->publicDir(__DIR__ . '/public');   // /build/app.css, /favicon.ico, /robots.txt
$http->fallback($kernel);                // everything else
```

Go serves the files; no PHP runs for them. Only GET and HEAD requests for
regular files are served. PHP files (`index.php`) and hidden files and
directories (`.env`, `.git/`) are never served as files: those paths go to the
app. Paths cannot leave `$dir`, and symlinks that point outside it are not
followed.

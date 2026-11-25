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
`examples/frameworks`. PSR-15 apps find their PSR-7 objects by themselves:
Cairo builds the request with nyholm/psr7, guzzlehttp/psr7,
php-http/discovery, laminas-diactoros (Mezzio) or slim/psr7, whichever is
installed. Which apps were tested, and how: [Compatibility](compatibility.md).

## Symfony, through its front controller

A Symfony app needs no `server.php`. Install the runtime package, as for
FrankenPHP's `runtime/frankenphp-symfony`:

```sh
composer require cairophp/symfony-runtime
```

name its runtime class in `composer.json` (then `composer dump-autoload`), or
in `APP_RUNTIME` in the environment:

```json
"extra": {
    "runtime": {
        "class": "Cairo\\Symfony\\Runtime"
    }
}
```

and serve the app's own front controller:

```sh
cairo serve public/index.php
```

Symfony's `public/index.php` hands the app to its Runtime component
(`vendor/autoload_runtime.php`), which makes the runtime class it was given.
Under `cairo serve`, `Cairo\Symfony\Runtime` builds the HTTP server for the
kernel, with `public/` as the [document root](#the-document-root), and serves
it on every PHP thread; anywhere else (`bin/console`, PHP-FPM, tests) it is
Symfony's own runtime, so nothing else changes. `.env` files are read as
Symfony reads them. The package is
[cairophp/symfony-runtime](https://github.com/cairophp/symfony-runtime); it
needs a Cairo newer than 0.5.0 (with `App::serve()`).

The runtime takes options from `APP_RUNTIME_OPTIONS` (JSON) or from
`extra.runtime` in `composer.json`, as Symfony's own runtimes do:

| Option | Default | |
|---|---|---|
| `listen` | `:8080` | The address of the HTTP server |
| `concurrency` | `isolated` | `isolated`: one request at a time per PHP thread. `fibers`: many, each with a kernel of its own |
| `threads` | Cairo's default | PHP threads |
| `max_requests` | none | Recycle a thread after this many requests ([supervision](supervision.md)) |

```sh
APP_RUNTIME_OPTIONS='{"listen":":80","threads":16}' cairo serve public/index.php
```

```json
"extra": {
    "runtime": {
        "class": "Cairo\\Symfony\\Runtime",
        "listen": ":8080",
        "concurrency": "fibers"
    }
}
```

In isolated mode one kernel serves the requests of its thread one after
another, and Symfony resets the services that hold a request's state
(`kernel.reset`) before each new one, as under FrankenPHP's worker mode. In
fiber mode a thread runs many requests at once and gives each request in
flight a kernel of its own: a kernel's services never hold two requests. A
kernel goes back to its thread after `terminate()`. Each kernel has its own
container, so a thread with many requests in flight holds that many
containers.

Fiber mode is for apps whose code is fiber-safe: no request state in static
properties. It is not for apps with sessions. Symfony's sessions are PHP's
own (`session_start()`), which a whole thread shares, so two requests of one
thread would share one session. Keep apps with sessions, such as one with a
login form, in isolated mode.

`--watch` and the [reload signal](reload.md) work with the front controller:
the app's directory is the one above `public/`.

For more than these options (gRPC servers, metrics, middleware), write a
`server.php` and give it the kernel: `$http->fallback($kernel)`, as above.

A framework's runner of your own can do what the package does: build a
`Cairo\\App` in the file that `cairo serve` runs and call `$app->serve()`,
which serves until the thread is told to stop and then returns, instead of
returning the App (`examples/serve`).

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

# Compatibility

Apps and frameworks that were run on Cairo, how they were served, and what
was checked. "In CI" means an end-to-end test of the Cairo repository serves
it on every change. "By hand" means it was checked once on the version
named, with the Cairo of that date.

| App or framework | Version | How it is served | Mode | Checked | Where |
|---|---|---|---|---|---|
| Symfony demo app (symfony/symfony-demo) | 3.1, Symfony 8.1, Doctrine ORM 3.6, Twig 3.27 | `cairo serve public/index.php` with cairophp/symfony-runtime | isolated | Home page, blog list and post pages, 404 page, logging in through the form, the admin area with the session | By hand, 2026-11-24 |
| Symfony, a kernel of its own (the package's `tests/fixture`) | Symfony 7.4 or 8 (Composer resolves the newest for its PHP) | `cairo serve public/index.php` with cairophp/symfony-runtime | isolated and fibers | Routes, the document root, forms, 404, one kernel per request in flight (20 requests of 0.5 s on one thread), recycled threads, sessions refused in fiber mode | The package's tests, against each Cairo change it depends on |
| Symfony kernel given to `server.php` (`examples/frameworks`) | Symfony HttpFoundation 6.4 or 7 | `$http->fallback($kernel)` | fibers | Requests, uploads, cookies, streamed and file responses | In CI |
| Laravel through Octane (cairophp/laravel-octane) | Laravel 13.43 | `php artisan octane:start --server=cairo` | isolated and fibers | The driver's 16 tests: requests, workers, `octane:reload`, `--watch`, `--max-requests`, stop | By hand, against each Cairo change to the driver |
| Slim | 4.15 with slim/psr7 1.8 | `$http->fallback($slimApp)` | fibers | Route parameters, a JSON body, the query string, 404, 20 requests of 0.5 s on one thread at once | By hand, 2026-11-24 |
| Mezzio | 3.29 with laminas-diactoros 3.10, FastRoute | `$http->fallback($mezzioApp)` | fibers | Route parameters, a raw body, the query string, 404, 20 requests of 0.5 s on one thread at once | By hand, 2026-11-24 |
| WordPress | 6.8.3, MariaDB | [classic mode](classic.md), `$http->scripts()` | classic | The installer, home page, posts, comments, search, feed, logging in, the dashboard and its settings, pretty permalinks, the REST API (creating and listing posts), a media upload, wp-cron, the plugins page; `wp-config.php` is never sent | By hand, 2026-11-25 |
| Scripts of their own (`examples/classic`) | | classic mode, `$http->scripts()` | classic | Fresh state for each request, routing (scripts, `PATH_INFO`, directories, the front controller, hidden files), forms, `php://input`, cookies, sessions, `exit()` and shutdown functions, a fatal error, fibers inside a request | In CI |
| Any PSR-15 handler (`examples/frameworks`) | nyholm/psr7 | `$http->fallback($handler)` | fibers | Requests, multipart uploads, attributes, streamed bodies | In CI |

## What does not run yet

- **Laravel without Octane.** `$http->fallback($laravel->make(Kernel::class))`
  answers requests, but nothing resets the app between them: the logged-in
  user, singletons and changed config of one request are there for the next.
  Use the Octane driver.
- **Symfony in fiber mode with sessions.** PHP has one session per thread,
  and the requests in flight on a thread would share it. cairophp/symfony-runtime
  refuses to start an app with `framework.session` in fiber mode;
  serve it in isolated mode, the default.

## Not tested yet

API Platform, CakePHP, CodeIgniter, Laminas MVC, Yii, Spiral, Drupal and
phpMyAdmin have not been run on Cairo. API Platform and Symfony apps in general are served the same way
as the Symfony demo; the PSR-15 frameworks the same way as Slim and Mezzio; Drupal and other script
apps the same way as WordPress, in classic mode.
If you run one of them, a report of what worked and what did not is welcome as
an issue in cairophp/cairo.

## Checking an app yourself

- Serve it in isolated mode first. Turn on fiber mode only for code that keeps
  no request state in static properties, globals or singletons, and turn on
  `$app->detectLeaks()` while you try it: it names the statics that change
  between requests ([Isolated mode](isolated-mode.md), [Fiber-local
  state](request-local.md)).
- A C extension that opens its own sockets blocks the thread in fiber mode:
  `$app->detectBlocking()` finds it ([Blocking detector](blocking.md)).
- Run its console with the same binary: `cairo php bin/console` or
  `cairo php artisan` ([PHP command line](cli.md)).

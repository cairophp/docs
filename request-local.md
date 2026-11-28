# Request-local statics

A PHP thread runs many requests at once, one fiber each, and a static
property belongs to its class, so every request on the thread sees the same
value. Code that keeps request state in a static (the current tenant, user
or app instance) would read another request's value:

1. Request A sets `Tenant::$current = 'alice'` and waits on a query.
2. Request B runs on the same thread and sets `Tenant::$current = 'bob'`.
3. A resumes and reads `bob`.

Register such statics in `server.php`, and each request keeps its own value:

```php
use Cairo\RequestLocal;

RequestLocal::register(Tenant::class, 'current');   // before the server starts

$http->get('/orders', function () {
    Tenant::$current = $tenant;   // seen by this request and its async() tasks only
    // ...
});
```

- Each request starts with the value the property had when the server
  started. Objects are shared, as they would be anyway, and arrays are copied
  on write.
- What a request sets is seen by it and by its `async()` tasks, and dropped
  when the request ends.
- Any visibility works, so a package's `protected static` can be registered.
  A subclass that inherits a static shares its parent's slot.
- Register in `server.php`, before the server starts. Every PHP thread runs
  it, so every thread registers its own.

Statics nobody registered stay shared. A package that keeps request state in
one must have it registered, or it must run in [isolated mode](isolated-mode.md).

## How it works

When fibers of two different requests take turns on a thread, a fiber switch
observer in C moves each registered static's value out to the request that
stopped and moves the next request's value in. These are plain value moves:
no copies and no refcounting. A switch between fibers of the same request,
or any switch on a thread with nothing registered, costs one comparison.
With three statics registered, a fiber switch between requests took about
15 ns more (60 ns → 75 ns). Plain-text and PostgreSQL requests per second
were unchanged with nothing registered.

## The environment

`putenv()` is request-local the same way, in fiber and isolated mode: each
request starts from the environment `server.php` left (the process's, with
what `server.php` set with `putenv()` while the thread booted), its own
`putenv()` calls are seen by its `getenv()` only, and they are gone when it
ends. A library that calls `putenv()` once, behind a static of its own,
should do so while the app boots, not in its first request. `.env` loaders
such as phpdotenv run while the app boots, so their values reach every
request.

## Finding statics that hold request state

A package that hides request state in a static you did not register leaks
it silently: nothing crashes, and one user sees another's data. In
development, turn on the detector:

```php
$app->detectLeaks();
```

When a request ends, Cairo reads every static property of the app's classes,
a few levels into arrays and objects, and compares it with its value when the
previous request ended. It logs the ones that look like request state:

```
level=WARN msg="static changed by a request" route="GET /orders" static=App\Tenant::$current
```

- A value that was set and is then replaced again, such as the current
  tenant, is reported. So is a list that keeps growing.
- A value set once and kept (a lazy singleton or a setting), a cache that
  only gains keys, and a static that is cleared are not reported.
- Registered statics and Cairo's own are skipped. Skip others with
  `detectLeaks(ignore: ['Vendor\Thing::$cache'])`.
- Each static is logged at most once a minute.

It works in both modes: in isolated mode a static also carries over from one
request to the next. It reads every static on every request (about 3 ms on a
Laravel app), so keep it off in production. It only sees code that ran, so
exercise the app (its test suite, or a load test) with it on.
`examples/leaks` has a static that leaks, a growing list, a cache and a
registered static.

## Laravel

[cairophp/octane](https://github.com/cairophp/octane) runs Laravel Octane in
fiber mode: each request in flight gets its own booted app, and the statics
an app sets (the facade root, Eloquent's booted models, the closures service
providers set while the app boots) are registered and kept per app. Run it
with `php artisan octane:cairo --mode=fibers --detect-leaks` to check your
app's packages.

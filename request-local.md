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

This is the first step to running Laravel without isolated mode: a bridge
will register `Facade::$app` and `Container::$instance` and give each request
its own app.

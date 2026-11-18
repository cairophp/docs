# Request state: Context values

Globals and static properties are shared by every fiber on a thread, so
request state goes on the context instead:

```php
use Cairo\Context;

Context::set('user', $user);                 // this fiber and the tasks it starts
Context::get('user');                        // null (or a default) when unset
Context::has('tenant');
Context::getOrSet('db', fn () => $pool->get());
Context::defer(fn () => $pool->put(Context::get('db')));   // when the fiber ends
```

Values follow Go's `context.WithValue`: an `async()` task sees its parent's
values, and a value it sets stays in the task. Deferred callbacks run last
first when the fiber ends; for a request, that is after the response is sent.

Rules that keep fibers safe: per-request data lives on `Request` and
`Context`, not in superglobals (Cairo does not fill `$_GET`/`$_SERVER`), and
blocking calls that are not hooked yet stall every fiber on their thread. Use `Cairo\offload()` for CPU-heavy work.

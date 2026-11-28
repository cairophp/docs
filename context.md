# Context and deadlines

`Cairo\Context::current()` (also passed to handlers) exposes the call's
deadline: `remaining()`, `deadline()`, `err()`, `throwIfDone()`. A Cairo I/O
call that is still waiting when the deadline passes throws
`Cairo\Context\DeadlineExceeded`, which becomes `DEADLINE_EXCEEDED` for gRPC
and `504` for HTTP.

Code that never waits (a CPU loop, a runaway recursion) is stopped too. When
the deadline passes, Go interrupts the request's PHP thread, and at the next
loop iteration or function call the request's fiber gets
`Context\DeadlineExceeded`, so it can clean up. If the code catches it and
carries on, 50 ms later the fiber is unwound the way `exit()` does it: catch
and `finally` blocks are skipped and destructors run. Only that request
stops; other fibers on the thread carry on. The same applies to its
`async()` tasks. Cairo's own runtime code is never interrupted. A single
long call into C (one huge `preg_match()` or `sort()`) runs to its end
before the check.

A part of a request can get its own, shorter budget, as with Go's
`context.WithTimeout`:

```php
$profile = $ctx->withTimeout(0.3)->run(function () use ($client) {
    return $client->get('http://profiles/me');   // gives up after 0.3s
});

$c = $ctx->withCancel();
$task = $c->run(fn () => async(fn () => crawl($urls)));
// ...
$c->cancel();   // the crawl's waiting calls throw Context\Canceled
```

`withTimeout()`, `withDeadline()` and `withCancel()` return a child context.
It ends at its own deadline, on `cancel()`, or when the context it came from
ends. `run($fn)` makes it the current context while `$fn` runs. Every Cairo
call waiting there (HTTP, gRPC, sockets, SQL, `sleep()`, channels) then
throws when it ends, and `async()` tasks started there inherit it. The
request goes on afterwards. Only the request's own deadline stops code that
never waits. `$ctx->done()` is a channel that closes when the context ends,
for `select()`. `$ctx->value('request_id')` reads values that Go middleware
attached to the request. Values your own code stores use `Context::set()` and
`Context::get()`.

<!-- illustration: context -->

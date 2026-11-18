# Concurrency API

```php
use function Cairo\{async, await, all, sleep, offload};

[$a, $b] = await(all([
    async(fn () => fetchUser($id)),     // each async() fiber gets its own goroutine
    async(fn () => fetchOrders($id)),
]));
```

`Cairo\Channel` passes values between fibers on the same PHP thread, as Go
channels do. `new Channel()` is unbuffered: `send()` waits for a receiver.
`new Channel(10)` buffers ten values. `select()` waits on several channels at
once:

```php
use Cairo\Channel;
use function Cairo\{async, select};

$jobs = new Channel(100);
async(function () use ($jobs) {
    foreach ($ids as $id) {
        $jobs->send($id);
    }
    $jobs->close();
});
foreach ($jobs as $id) { /* until closed and drained */ }

[$key, $value, $ok] = select([
    'job'  => $jobs,                // receive
    'out'  => [$results, $row],     // send
    'done' => $ctx->done(),         // closed when the request's context ends
], timeout: 0.5);                   // [null, null, false] after 0.5s; 0 never waits
```

A waiting fiber is suspended, not the thread. The wait also ends when the
request's context ends: with `$ctx->done()` among the cases, select() returns
that case; otherwise it throws `Context\DeadlineExceeded` or
`Context\Canceled`. After `close()`, receivers get what is buffered, then
`recv()` throws `Channel\Closed` (select() returns `ok` false), and `send()`
throws `Channel\Closed`. `trySend()` and `tryRecv()` never wait. Values stay
in PHP and are not copied, so a channel cannot cross PHP threads; use
`offload()` for that.

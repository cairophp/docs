# Streamed answers, Server-Sent Events and files

A handler usually returns its whole answer. These are the ways to send one
while the handler still runs, to leave a file to Go, and to read a request
while its client still sends it.

## A body that is sent in pieces

```php
use Cairo\Http\Response;
use Cairo\Http\Stream;

$http->get('/export', fn (): Response => Response::stream(function (Stream $out): void {
    foreach (rows() as $row) {
        $out->write(json_encode($row) . "\n");
    }
}, headers: ['Content-Type' => 'application/x-ndjson']));
```

The client has the status and the headers before the function runs, then
every `write()` as it is made, and the answer ends when the function
returns. There is no `Content-Length` unless you set one.

- **Each stream is a fiber.** One PHP thread serves as many streams as it
  has clients: fifty streams that each wait a second between two pieces take
  one thread a second.
- **A slow client holds back only its own handler.** `write()` returns at
  once while Go has room for the piece (64 pieces wait there at most), and
  waits behind a client that reads slowly.
- **A client that leaves ends its handler.** The next `write()`, and any
  wait, throws `Cairo\Context\Canceled`. Catch it only to clean up.
- **A handler that fails after the head was sent** cannot change the status
  any more. Cairo logs the error and cuts the connection, so the client sees
  an answer that is not whole instead of one that only looks complete.

A route whose answers are cached (`->cache()`) cannot stream: several
requests share its answer.

### Time limits

`Middleware::timeout()` ends a request that takes too long, a stream too.
Take the routes that stream for long out of it:

```php
$http->use(Middleware::timeout(10));
$http->get('/events', $handler)->noTimeout();
```

The server's write timeout (`$http->timeouts(write: 30)`) does not end a
stream that is alive. It bounds each write of a stream instead: a client
that reads, however slowly, stays, and one that stops reading for that long
is dropped.

A server that stops does not wait for its streams, which have no end of
their own. Each is refused its next `write()` or `send()` with
`Context\Canceled`, as when its client has left: the handler ends, what it
had sent is delivered, and the client connects again, to the new server.
A handler that neither writes nor ends holds the stop for the grace time
(`--grace`, 30 seconds), so let a quiet stream send a comment now and then.

## Server-Sent Events

```php
use Cairo\Http\Events;

$http->get('/events', fn (Request $req): Response => Response::events(function (Events $events) use ($req): void {
    $last = (int) ($req->header('Last-Event-ID') ?? 0);
    while (true) {
        foreach (newsSince($last) as $item) {
            $events->send(json_encode($item), event: 'news', id: (string) ($last = $item['id']));
        }
        $events->comment();          // keeps a proxy from closing a quiet stream
        Cairo\sleep(15);
    }
}))->noTimeout();
```

In the browser this is `new EventSource('/events')`. `send()` takes the
data, an event name for `addEventListener()` and an id, which the browser
sends back as `Last-Event-ID` when it connects again; `retry()` tells it how
long to wait before it does. Data with line breaks is sent as the standard
says, one `data:` line each. The loop above ends when the client leaves:
`send()` and `sleep()` throw `Context\Canceled`.

`Response::events()` sets `Content-Type: text/event-stream`,
`Cache-Control: no-cache` and `X-Accel-Buffering: no` (for an nginx in
front).

### How many streams a thread holds

A stream that waits costs its PHP thread no time, but it holds memory for as
long as it is open: a fiber, about 22 KB of PHP memory, and about 52 KB of
the process in all (measured with the handler above, idle). PHP's
`memory_limit` counts per PHP thread, so the default of 128M is reached at
about 5,700 open streams on one thread. Reaching it is a fatal error: it
ends the thread, and with it every stream the thread holds
([Thread supervision](supervision.md)).

For thousands of streams, give the threads the memory in `php.ini`
(`memory_limit = 1G` is room for about 45,000 streams a thread), or cap
what a thread takes with `$app->maxInFlight()`: requests over the cap wait
in Go and none of them fails, but the cap counts every request, so a thread
full of streams lets nothing else in. The process also needs a file
descriptor for each connection (`ulimit -n`), and Linux gives a process
65,530 memory mappings unless `vm.max_map_count` is raised, which is about
32,000 fibers in the whole process.

When the clients mostly wait for the same events, they need no fiber at
all: [`Response::eventsFrom()`](websockets.md#topics) names the topics a
client listens to, and Go serves it from there.

## Early Hints

A browser can start on what a page needs while the handler still makes the
page:

```php
$http->get('/', function (Request $req): Response {
    $req->earlyHints(['Link' => '</app.css>; rel=preload; as=style']);
    return Response::html(renderHome());
});
```

This sends `103 Early Hints` with those headers at once. They are the
hint's alone: the answer names its own headers.

## Classic PHP: echo, flush() and friends

In [isolated mode](isolated-mode.md), what a handler echoes is its answer,
and the functions that PHP code already uses for streaming work as under
any PHP server:

```php
$http->get('/report', function (): void {
    header('Content-Type: text/plain');
    foreach (parts() as $part) {
        echo $part;
        flush();                       // the client has it now
    }
});
```

| Function | What it does |
|----------|--------------|
| `flush()` | Sends the status, the headers and what was echoed so far. After it `headers_sent()` is true. With output buffers of your own, call `ob_flush()` first, as elsewhere |
| `headers_send(103)` | Sends the headers set with `header()` as Early Hints. Symfony's `Response::sendHeaders(103)` uses it |
| `fastcgi_finish_request()` | Sends the answer written so far as the whole answer; the code after it runs on, with the database and everything else that waits |

An answer that is never flushed is sent whole, with its length, as before.
Output grows no larger than 8 KiB before it is sent once a stream has begun.

In fiber mode, work after the answer goes in `Context::defer()`, and it may
wait as a handler may.

## Files that Go sends

Sending a large file from PHP keeps a handler busy for as long as the
client downloads. Name the file instead, and Go sends it:

```php
$http->sendfile(__DIR__ . '/storage/downloads');

$http->get('/invoices/{id}', function (Request $req): Response {
    $invoice = authorize($req);
    return Response::file($invoice->path, ['Content-Disposition' => 'attachment; filename="invoice.pdf"']);
});
```

The handler returns at once and its PHP thread is free; Go sends the file
with ranges (a download that resumes, a video that seeks) and
`If-Modified-Since`. The content type is the file name's unless the answer
sets one.

- **Only under a declared directory.** `$http->sendfile($dir)` names a
  directory whose files may be sent, and may be called more than once. A
  path outside them, through `..` or through a symlink that leaves the
  directory, is answered with 404 and a line in the log.
- **`X-Sendfile`.** `Response::file()` is the header `X-Sendfile` with the
  file's path, which code written for Apache already sets. Classic PHP does
  it with `header('X-Sendfile: ' . $path)`.
- **`X-Accel-Redirect`.** Code written for nginx names a URL instead.
  `$http->sendfile($dir, '/protected')` maps `X-Accel-Redirect:
  /protected/a/b.pdf` to `$dir/a/b.pdf`.
- **Symfony and Laravel.** Their file responses (`BinaryFileResponse`,
  `response()->download()`, `response()->file()`) are sent by PHP in pieces
  by default, ranges included. Call
  `BinaryFileResponse::trustXSendfileTypeHeader()` once at start and they
  leave the file to Go: with `sendfile()` declared, Cairo sets the
  `X-Sendfile-Type` request header that they look for, and removes what a
  client sent under that name.

Without `sendfile()` both headers are ordinary headers and go to the client
or to the proxy in front of Cairo, as before.

## A request body that is read as it arrives

A request's body is read whole before its handler runs, 32 MiB at most.
`->streamBody()` gives the handler the body as it arrives instead:

```php
$http->put('/videos/{id}', function (Request $req): Response {
    $file = fopen(target($req), 'wb');
    while (($piece = $req->read()) !== null) {
        fwrite($file, $piece);
    }
    return Response::json(['stored' => true], 201);
})->streamBody();
```

`read()` returns the next piece (64 KiB at most by default, 1 MiB at most)
and `null` once the client has sent everything. It waits, its fiber only,
while the client sends. On such a route `body()` is empty and a form is not
parsed; neither the 32 MiB limit nor the server's read timeout applies, so
the handler decides how much it accepts and stops reading when it has
enough.

The handler may answer while it reads. Together with `Response::stream()`
that is a conversation over one request, on HTTP/1 as well as HTTP/2:

```php
$http->post('/translate', fn (Request $req): Response => Response::stream(function (Stream $out) use ($req): void {
    while (($piece = $req->read()) !== null) {
        $out->write(translate($piece));
    }
}))->streamBody()->noTimeout();
```

Few HTTP/1 clients read an answer before they have sent their whole
request; browsers do not. Use it between your own services.

## Frameworks

Symfony's `StreamedResponse` and Laravel's `response()->stream()`,
`response()->eventStream()` and `response()->streamDownload()` are sent
while their callback writes, in both modes and through the
[Octane driver](frameworks.md); a PSR-7 body of unknown size, or above
1 MiB, is read and sent in pieces. See [Frameworks](frameworks.md).

See `examples/streaming` in the repository for all of the above.

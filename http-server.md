# HTTP server limits

Go's HTTP server serves every connection, so its limits are what stand
between a client and the PHP threads. They are set on the server you
declare:

```php
$http = $app->http(':8080');
$http->timeouts(read: 30, write: 30, header: 10, idle: 120);
```

| Argument | Default | What it bounds |
|----------|---------|----------------|
| `read` | 0 (none) | Reading a whole request, its head and body |
| `write` | 0 (none) | Writing an answer; for a [streamed answer](streaming.md) or a [WebSocket](websockets.md), each piece that is written |
| `header` | 10 | Reading a request's head: a client that has not sent its headers within this many seconds is cut |
| `idle` | 120 | How long a kept-alive connection may wait for its next request before it is closed |

All are in seconds, and 0 turns the limit off. A negative value is refused
when `server.php` runs.

`header` and `idle` are on by default so that a server reached straight from
the internet is safe without a proxy in front: without them, a client that
sends its head one byte at a time, or that opens connections and leaves
them, keeps them open for as long as it likes (slowloris). A connection that
is streaming an answer, a WebSocket or a [Mercure](mercure.md) subscription is
not idle, and neither limit ends it.

gRPC servers close a connection that has had no call for 2 minutes, with a
GOAWAY that a client answers by connecting again on its next call.

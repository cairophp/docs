# WebSockets and topics

A WebSocket is a connection that stays open, on which the server and the
client send each other messages whenever they like. On Cairo a WebSocket
is served by a fiber of PHP, so one PHP thread holds as many of them as it
has clients. Topics are the other half: PHP publishes a message once, and
Go sends it to every client that listens.

## A WebSocket in a handler

```php
use Cairo\Http\Request;
use Cairo\Http\Response;
use Cairo\Http\WebSocket;

$http->get('/echo', fn (Request $req): Response => Response::websocket(function (WebSocket $ws): void {
    while (($message = $ws->receive()) !== null) {
        $ws->send(strtoupper($message->data));
    }
}))->noTimeout();
```

In the browser this is `new WebSocket('wss://example.com/echo')`. The
function runs in the request's fiber with the socket, and the socket closes
when it returns.

| Call | What it does |
|------|--------------|
| `$ws->receive()` | The next message of the client, a `Message` with `data` and `binary`. It waits, its fiber only, until one arrives, and returns `null` once the client has closed or gone |
| `$ws->send($data, binary: false)` | Sends a text message, which must be UTF-8, or a binary one |
| `$ws->close($code = 1000, $reason = '')` | Closes with a status of your choosing: the standard's, or 3000 to 4999 for your app's own. A handler that just returns closes with 1000, one that throws with 1011 |
| `$ws->protocol` | The subprotocol that was agreed on, `''` for none |
| `$ws->subscribe(...$topics)`, `unsubscribe(...$topics)` | See [Topics](#topics) |

- **Each socket is a fiber.** Fifty sockets whose handlers each wait a
  second share one PHP thread and are done after one second. A handler may
  query a database, call another service or sleep between two messages
  like any handler.
- **A slow client holds back only its own handler.** `send()` returns at
  once while Go has room for the message (64 wait there at most), and waits
  behind a client that reads slowly. What the client sends is read ahead of
  PHP, 64 messages or 1 MiB at most; a client that sends faster than its
  handler receives is held back by TCP.
- **A client that leaves does not cut its handler off.** `receive()` still
  returns what the client had sent, then `null`, and `send()` throws
  `Cairo\Context\Canceled`. So a message that a page sends just before it
  closes is worked on to the end. (A streamed answer is different: there
  the client's leaving ends every wait of the handler.) A handler that
  only sends learns that its client left at its next `send()`.

### Who may connect

The route's handler runs first, as for any request, and only a
`Response::websocket()` makes the handshake. So the handler decides who
gets a socket, with whatever it has for that: a cookie, a token, the
middleware of the server.

```php
$http->get('/chat', function (Request $req): Response {
    $user = userOf($req);
    if ($user === null) {
        return Response::text('sign in first', 401);
    }
    return Response::websocket(fn (WebSocket $ws) => chat($ws, $user));
})->noTimeout();
```

A browser sends cookies with a WebSocket's handshake wherever the page
comes from, so a page of another site could open a socket as your user.
Cairo therefore refuses a handshake whose `Origin` is not the request's own
host (403), unless you name it:

```php
Response::websocket($handler, origins: ['app.example.com', '*.example.org']);
```

A pattern is a host, with `*` for any run of characters. A client that
sends no `Origin`, which is every client that is not a browser, is not
refused by this: check its token in the handler.

`protocols: ['chat.v2', 'chat.v1']` are the subprotocols the client may
choose from, in your order of preference; `$ws->protocol` says which it
chose.

### A server that is only WebSockets

A server needs no other routes than its sockets, and `fallback()` answers
with a socket on every path:

```php
$ws = $app->http(':9000');

$ws->fallback(function (Request $req): Response {
    $room = 'room.' . trim($req->path(), '/');   // ws://host:9000/42 is room.42
    return Response::websocket(function (WebSocket $socket) use ($room): void {
        $socket->subscribe($room);
        while (($message = $socket->receive()) !== null) {
            Topic::publish($room, $message->data);
        }
    });
});
```

A route of `GET /` matches every path that no other route does, so it
would take these requests before the fallback sees them: write the root
alone as `/{$}`.

### Limits

| Option of `Response::websocket()` | Default | What it bounds |
|-----------------------------------|---------|----------------|
| `maxMessage` | 65536 | The bytes of one message of the client. A larger one closes the socket with 1009 |
| `ping` | 30.0 | Go pings the client every so many seconds and drops one that does not answer, so a client that vanished without closing does not hold its handler for ever. 0 for no pings |

`Middleware::timeout()` ends a request that takes too long, a WebSocket
too: give the route `->noTimeout()`. The server's write timeout
(`$http->timeouts(write: 30)`) bounds each message that is written, not the
socket: a client that stops reading for that long is dropped.

A server that stops closes its sockets with status 1001 (going away):
`receive()` returns `null`, the handlers end, and the clients connect
again, to the new server. A handler that neither receives nor sends holds
the stop for the grace time (`--grace`, 30 seconds).

### What a socket costs

An open socket whose handler waits in `receive()` holds a fiber: about
24 KB of PHP memory, and about 60 KB of the process in all (measured with
5,000 idle sockets). PHP's `memory_limit` counts per PHP thread, as for
[streams](streaming.md#how-many-streams-a-thread-holds): the default of
128M is room for about 5,300 sockets on one thread, and what is said there
about `memory_limit`, `$app->maxInFlight()`, file descriptors and
`vm.max_map_count` holds for sockets too. Clients that only listen need no
fiber at all: see [Topics](#topics).

Measured with an echo handler on one PHP thread, the server on two CPUs
and the clients on two others, with messages of 100 bytes: one client that
waits for each echo makes 7,700 round trips a second (0.11 ms each), and
64 clients, or 1,000, make 67,000 a second together.

### What is not there

- **Compression of messages** (`permessage-deflate`). It costs memory for
  every socket, and is left off.
- **WebSockets over HTTP/2.** A browser opens a WebSocket on a connection
  of its own, with HTTP/1.1, also to a server that speaks HTTP/2; nothing
  is to be done for it. A proxy in front must pass the `Upgrade` and
  `Connection` headers on, as for any WebSocket server.
- **A route with `->cache()`** cannot be a WebSocket.
- **[Isolated mode](isolated-mode.md)** serves one request per PHP thread
  at a time, and a socket is a request for as long as it is open: use fiber
  mode for sockets. `Response::eventsFrom()` below holds no thread in
  either mode.

## Topics

Most of what goes to many clients is the same for all of them: a price, a
chat message, a notification. For that, the handler of each client should
not have to run at all:

```php
use Cairo\Http\Topic;

// Anywhere: a handler, a deferred task, a script's fiber.
$listening = Topic::publish('room.42', json_encode($message));
```

`publish()` is one call that does not wait for any client. Go sends the
message to every client that listens to the topic, and the call returns
how many do. Two kinds of clients listen.

**WebSockets that subscribed.** They get the message as a text message:

```php
$http->get('/rooms/{room}', function (Request $req): Response {
    $room = 'room.' . $req->param('room');
    return Response::websocket(function (WebSocket $ws) use ($room): void {
        $ws->subscribe($room);
        while (($message = $ws->receive()) !== null) {
            Topic::publish($room, $message->data);   // to every member, this one too
        }
    });
})->noTimeout();
```

The fiber of a member only receives; it does not run when another member
speaks. Publishing does not wait, so a message that a handler sends
itself with `send()` may reach its client before one that was published
just before it.

<!-- illustration: topics -->

**Server-Sent Events that Go serves alone.** The handler says who may
listen to what, and ends:

```php
$http->get('/notifications', function (Request $req): Response {
    $user = userOf($req);
    if ($user === null) {
        return Response::text('sign in first', 401);
    }
    return Response::eventsFrom(['news', "user.$user"]);
});
```

In the browser this is `new EventSource('/notifications')`. From here Go
serves the client: no fiber and no PHP memory for as long as it listens,
in isolated mode too. Such a listener costs about 36 KB of the process
(measured with 10,000 of them), against 52 KB for a stream that a fiber
serves ([`Response::events()`](streaming.md#server-sent-events)), and a PHP
thread's `memory_limit` does not count it.

`publish($topic, $data, event: 'price', id: '17')` names the event for
`addEventListener()` and gives it an id; a WebSocket gets `$data` alone.
`eventsFrom()` sends a comment every 15 seconds (`keepAlive:`), so that no
proxy closes a quiet connection, and sets the headers that
`Response::events()` sets. Go ends these answers when the server stops, and
the browser connects again.

### Who may listen

A topic's name is yours to choose, and nothing but your handler stands
between a client and a topic: `subscribe()` and `eventsFrom()` are called
by your code, with names it builds. Never take a topic's name from the
client without checking that this client may hear it.

### What topics are, and what they are not

| | |
|---|---|
| A topic's name | 1 to 256 bytes |
| Topics one client listens to | 64 at most |
| A published message | 1 MiB at most; an event's name and id are one line of 256 bytes at most |
| Messages that wait for one client | 64. A client that reads more slowly than its topics are published to is dropped, and connects again: one slow client never holds back the others or the publisher |
| Messages that wait to be handed out | 1024. `publish()` waits, its fiber only, when they are full |
| Order | Every listener gets the messages of its topics in the order they were published |

- **The topics are one server process's.** A message that is published in
  one process reaches the clients of that process. With several servers
  behind a load balancer, publish in each.
- **Nothing is kept.** A client hears what is published while it listens;
  there is no history and no `Last-Event-ID` to catch up from. When a
  client must miss nothing, let it load the state when it connects and
  apply the events from then on, or serve it with
  [`Response::events()`](streaming.md#server-sent-events), where your code
  reads `Last-Event-ID`.

Measured with the server on two CPUs and the clients on two others: 100
messages of 100 bytes, published to 10,000 Server-Sent Events listeners,
had all arrived after 3.6 seconds, which is 278,000 deliveries a second;
to 5,000 WebSockets that subscribed, 227,000 a second.

## The example

[`examples/websocket`](https://github.com/cairophp/cairo/tree/main/examples/websocket)
has an echo, a chat room on a topic, a handshake that the handler refuses,
origins, subprotocols, and Server-Sent Events from topics.

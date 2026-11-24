# The Mercure hub

[Mercure](https://mercure.rocks) is a protocol for pushing updates to
browsers: a page subscribes to topics with an `EventSource`, and whatever
is published to a topic reaches all of its subscribers. A Cairo server can
be the hub itself. Go serves every subscriber, so a subscriber holds no PHP
thread, no fiber and no PHP memory, and PHP publishes with one function
call.

> **The license.** The hub is the Mercure.rocks hub
> ([dunglas/mercure](https://github.com/dunglas/mercure)), linked into the
> `cairo` binary. It is licensed under the **AGPL-3.0**, not under Cairo's
> Apache-2.0. A binary that contains it is a combined work: whoever passes
> that binary on, or lets users interact with it over a network, has the
> duties of the AGPL-3.0 for it. The releases and the official image contain
> the hub. See [A binary without the hub](#a-binary-without-the-hub) when
> that does not suit you. This is a description, not legal advice.

## A hub in a server

```php
$http = $app->http(':8080');

$key = getenv('MERCURE_KEY');   // a long random secret, never in the code
$http->mercure()
    ->publicUrls(['https://example.com'])
    ->issuer('https://example.com', publisher: $key, subscriber: $key)
    ->anonymous();

$http->post('/books', function (Request $req): Response {
    $book = saveBook($req->json());
    mercure_publish("https://example.com/books/{$book['id']}", json_encode($book));
    return Response::json($book, 201);
});
```

In the browser:

```js
const url = new URL('/.well-known/mercure', location.origin);
url.searchParams.append('match', 'https://example.com/books/1');
new EventSource(url).onmessage = (e) => show(JSON.parse(e.data));
```

The hub answers at `/.well-known/mercure`, as the protocol says, before any
route of yours; a route there is refused when the server starts. A process
has one hub.

| Setting | What it does |
|---------|--------------|
| `issuer($identifier, publisher:, subscriber:, algorithm: 'HS256')` | Trusts the tokens whose `iss` is `$identifier`. `publisher` verifies the token of a program that publishes with a POST, `subscriber` the token of a client that may hear private updates. A key is a secret for the HS algorithms, or a public key in PEM for the others. Call it once for each issuer |
| `anonymous()` | Clients without a token may subscribe. They get the updates that are not private |
| `publicUrls([...])` | The public URLs of the server (scheme and host). The hub answers for no other host (421) |
| `resource($url)` | The audience (`aud`) that tokens must name, when it is not the hub's URL as the client asked for it |
| `cors([...])`, `publishOrigins([...])` | The other sites whose pages may subscribe, and may publish with the token cookie |
| `history($file, size: 0)` | Keeps the updates in a file. See [History](#history) |
| `subscriptions()` | The subscription API and its events: who subscribes to what |
| `compatibility(8)` | Also takes clients and tokens from before Mercure 1.0. See [Clients from before 1.0](#clients-from-before-10) |
| `timeouts(heartbeat: 40, write: 600, dispatch: 5)` | Seconds: a comment to a quiet subscriber, how long a subscription lasts before the client connects again, and how long an update may take to reach a subscriber before it is dropped |
| `limits(total:, perToken:, perClient:)` | How many subscriptions may be open at once. 0 is no limit |
| `cookie($name)` | The name of the token cookie. The default, `__Secure-mercure_access_token`, travels over HTTPS only |
| `debugger()` | The hub's debugging page at `/.well-known/mercure/debug/`. Not for production |

A hub that nobody could subscribe to (no `anonymous()` and no subscriber
key) is refused when the server starts. So is a hub with `issuer()` and
neither `publicUrls()` nor `resource()`: the hub would take the audience
that tokens must name from the request's `Host` header, which is the
client's to choose.

## Publishing from PHP

```php
$id = mercure_publish(
    'https://example.com/books/1',   // a topic, or a list: the topic and its alternates
    json_encode($book),
    private: false,                  // true: only for subscribers whose token names a topic of it
    id: null,                        // the update's id; the hub makes one
    type: null,                      // the event's name, for addEventListener()
    retry: null,                     // milliseconds before the client connects again
);
```

It is the function FrankenPHP has, with the same parameters, so code and
libraries written for it publish on Cairo unchanged. It goes straight to
the hub in the same process: no HTTP, no token. Only the calling fiber
waits, and only until the hub has put the update in the queue of each
subscriber; it does not wait for the clients. It returns the update's id.
That takes longer the more subscribers the topic has: on two busy CPUs, 6 ms
for 1,000 of them and 80 ms for 10,000. A handler whose client need not wait
for that publishes after it answered, with `Context::defer()`.

- An update the protocol does not allow throws a `ValueError`: a topic below
  `/.well-known/mercure` or `*`, an id that starts with `#` or is `earliest`,
  the type `mercure`, data that is not UTF-8, a negative `retry`.
- A process without a hub throws a `RuntimeException`. That is every script
  of [`cairo php`](cli.md): a command publishes with a POST, as below.
- It works from a handler, from a task that runs on after the answer
  (`Context::defer()`), in fiber mode and in [isolated mode](isolated-mode.md).

## Publishing from another program

With a `publisher` key, the hub takes a POST at `/.well-known/mercure` with
the form fields `topic`, `data` and, when wanted, `private`, `id`, `type`
and `retry`, and a token in the `Authorization: Bearer` header. This is how
a command, a queue worker or another service publishes. Without a publisher
key the hub takes no POST at all, and only `mercure_publish()` publishes.

## Tokens

Since Mercure 1.0 a token is an OAuth 2.0 access token (a JWT): its header
says `"typ": "at+jwt"`, and its claims name the issuer (`iss`, the
`$identifier` of `issuer()`), the hub (`aud`, the hub's URL, such as
`https://example.com/.well-known/mercure`), an expiry (`exp`), and what it
allows:

```json
{
  "iss": "https://example.com",
  "aud": "https://example.com/.well-known/mercure",
  "exp": 1790000000,
  "authorization_details": [{
    "type": "https://mercure.rocks/authorization-detail",
    "actions": ["subscribe"],
    "topics": [{ "match": "https://example.com/users/42" }]
  }]
}
```

Your app signs such a token for a signed-in user and gives it to the
browser, in the cookie or for the `Authorization` header; any JWT library
does it. A token must expire, so make them as they are needed. The hub
answers 401 for a token it does not trust and 403 for one that does not
allow what was asked.

## History

Without `history()` nothing is kept: a client hears what is published while
it listens. With it, the updates are stored in the file (a
[bbolt](https://github.com/etcd-io/bbolt) database), and a client that comes
back with the id of the last update it saw gets what it missed, also after
the server was restarted. An `EventSource` sends that id by itself when it
reconnects. `size` is how many updates are kept, 0 for all of them. The
file belongs to one process: two servers cannot share it.

## Clients from before 1.0

Mercure 1.0 changed what clients send: `?match=` instead of `?topic=`, and
the tokens above instead of a `mercure` claim. A hub refuses the old forms
unless you say:

```php
$http->mercure()->compatibility(8);
```

With it, clients and tokens of the protocol's version 8 (the hubs 0.14 to
0.2x) work beside the new ones. It relaxes how tokens are checked, so it is
for the time it takes to move your clients, not for good. For Symfony, the
Mercure component speaks 1.0 from its version 0.8.

## Metrics and logs

On a process where a server has [`metrics()`](observability.md), the hub's
own are there too: `mercure_subscribers_connected`,
`mercure_subscribers_total`, `mercure_updates_total` and
`mercure_subscriptions_rejected_total`. A subscriber is no request of your
app: the hub's requests are not in `cairo_http_request_duration_seconds`,
not traced, and not ended by `Middleware::timeout()`.

The hub logs its warnings and errors (a signing key that is too short, for
one). It does not log each subscriber that comes and goes.

## What it is not

- **One process.** The hub's subscribers and its history are this
  process's. Several servers behind a load balancer are several hubs; the
  hub's authors sell transports that span processes.
- **Not Cairo's topics.** [`Topic::publish()`](websockets.md#topics) and
  `Response::eventsFrom()` are Cairo's own, simpler way to the same end,
  under Cairo's license: your handler decides who listens to what, and
  there are no tokens, no history and no protocol for other programs. They
  are also the faster of the two: to 10,000 listeners on the same machine,
  Cairo's topics delivered about 300,000 updates a second and the hub about
  120,000. The hub is for apps and libraries that speak Mercure.
- **Behind a proxy**, tell the hub its public URL with `publicUrls()` or
  `resource()`: it sees the scheme and the host of the proxy's request.
  Give the proxy no buffering and a long read timeout for
  `/.well-known/mercure`, as for any Server-Sent Events.

## A binary without the hub

Build Cairo with the Go build tag `nomercure`:

```sh
make build TAGS=nomercure                                   # native
docker build -f Dockerfile.static --build-arg CAIRO_TAGS=nomercure --output dist .
```

That binary contains no AGPL code. It refuses `$http->mercure()` when the
server starts, and has no `mercure_publish()`. Everything else is the same.
The hub's authors also sell it under other terms: see
[mercure.rocks](https://mercure.rocks).

## The example

[`examples/mercure`](https://github.com/cairophp/cairo/tree/main/examples/mercure)
is a hub with a page that listens and a route that publishes.

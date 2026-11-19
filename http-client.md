# HTTP client

`Cairo\Http\Client` sends requests through Go's `net/http`: pooled
keep-alive connections, HTTP/2 over TLS, and proxies from `HTTP_PROXY`,
`HTTPS_PROXY` and `NO_PROXY`. In a handler or `async()` task the fiber
suspends while Go waits, and the request's deadline cancels the call;
elsewhere (the declare phase, offload threads) the thread waits.

```php
use Cairo\Http\Client;

$api = new Client(['base_uri' => 'https://api.example.com', 'timeout' => 5, 'headers' => ['Authorization' => "Bearer $token"]]);

$user = $api->get('/users/42', ['query' => ['expand' => 'teams']])->json();
$res = $api->post('/users', ['json' => ['name' => 'Mohamed']]);
$res->status;               // 201
$res->header('Location');   // any case
$res->body;                 // string

[$a, $b] = Cairo\await(Cairo\all([
    Cairo\async(fn () => $api->get('/a')),
    Cairo\async(fn () => $api->get('/b')),
]));
```

Options, on the constructor or per request: `base_uri`, `headers`, `query`,
`body` / `json` / `form`, `timeout` (seconds, default 30), `follow_redirects`
(bool or a count, default 5), `verify` (bool or a CA bundle path) and `cert`
(a PEM path, or `[cert, key]`). Every status comes back as a response;
`Cairo\Http\ClientException` (with `->kind`: `connect`, `tls`, `timeout`,
`redirects`, `request`) means there was none. Bodies are read in full.

The connection pool lives in Go and is shared by every PHP thread, one per
set of TLS options, so all threads reuse the same keep-alive and HTTP/2
connections to a host.

## One upstream call for identical requests

```php
$rates = new Client(['base_uri' => 'https://rates.example.com', 'coalesce' => true]);
```

With `coalesce`, identical `GET` and `HEAD` requests in flight at the same
moment, from any fiber on any thread, share one upstream call and all get
its response. Under load a hot URL is fetched once per round trip instead of
once per request: in the benchmark, 256 concurrent requests to a 20 ms
upstream made 354 upstream calls instead of 88,000.

Identical means the same method, URL, headers (so the same `Authorization`
and `Cookie`), TLS options, redirects and timeout. Requests with a body never
share. Turn it on only for hosts whose answer depends on nothing else, such
as public or per-token data, and never for calls with side effects. A caller
that is cancelled or passes its deadline stops waiting without failing the
others, and the upstream call is cancelled when no caller is left. Results
are shared only while the call is in flight. To keep answers longer, cache
them (see [Response cache](response-cache.md)).

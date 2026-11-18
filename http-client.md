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

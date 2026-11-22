# Response cache

`->cache()` after a route lets Go answer repeated GET requests to it from
memory, without running PHP:

```php
$http->get('/products', $listProducts)
     ->cache(ttl: 5, staleWhileRevalidate: 30, vary: ['Accept-Language']);
```

- A response stays fresh for `ttl` seconds. For `staleWhileRevalidate` more
  seconds Go keeps serving it and rebuilds it with one request in the
  background, so no client waits for the rebuild.
- Identical requests that arrive while PHP builds a response wait for that
  one: 256 clients asking for the same page at once make one PHP call.
- The key is the route, host, path, raw query string and the `vary` request
  headers.
- It is safe by default: only GET, and only 200 responses without
  `Set-Cookie` or `Cache-Control: private`, `no-store` or `no-cache` are
  stored. A request with `Authorization` or `Cookie` skips the cache unless
  `vary` names that header.
- Each server keeps at most 64 MiB of responses (least recently used go
  first), and a response over 1 MiB is not stored.

Go middleware still runs on a cached request; values it passes to PHP (such
as the request id) are those of the request that built the response.

A HEAD request to a cached route is answered from what a GET stored; on a
miss PHP runs, and its answer is not stored.

A request that the cache answers is not read for PHP: Cairo looks in the
cache first and only then reads the request's body, so a GET that carries a
body gets the cached response whatever that body is. A request with a
`multipart/form-data` body never uses the cache.

## Purging by tag

A TTL bounds how old a response can be. To drop responses the moment their
data changes, give the route tags and purge them:

```php
use Cairo\Cache;

$http->get('/products', $listProducts)->cache(ttl: 60, tags: ['products']);
$http->get('/products/{id}', $showProduct)->cache(ttl: 60, tags: ['products']);

$http->post('/products', function (Request $r) use ($db): Response {
    $db->exec('INSERT INTO products ...');
    Cache::purge('products');
    return Response::json(['ok' => true], 201);
});
```

- `Cache::purge('a', 'b')` drops every cached response of the routes tagged
  `a` or `b`, on all HTTP servers of the process. The next request runs PHP.
- A response PHP was already building when the purge came is not stored, and
  requests that arrive after the purge do not wait for it.
- A purge costs the same however much is cached, so calling it on every
  write is fine. A tag no route declares is ignored.
- Tags belong to routes, not to single responses: purging `products` drops
  every page and query string of the tagged routes.

`examples/cache` has a runnable server with each of these.

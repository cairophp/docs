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

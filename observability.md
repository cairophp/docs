# Metrics, health probes and tracing

What a Cairo process reports of itself to the machines around it: numbers for
Prometheus to scrape, probes for an orchestrator or a load balancer, and
OpenTelemetry traces. Each is one line in `server.php`, Go does the work, and
none of it runs unless you declare it:

```php
$app->tracing(service: 'orders');                              // traces, sent with OTLP

$http = $app->http(':8080');                                   // the app
$http->get('/orders/{id}', [OrderController::class, 'show']);

$app->http('127.0.0.1:9100')->metrics()->health();             // for the monitoring only
```

The [slow request log](slow-requests.md), [heavy routes](heavy-routes.md)
and the [blocking detector](blocking.md) answer a different question: where
one request's time went, in the log.

## Metrics

`$http->metrics()` serves the metrics of the whole process at `GET /metrics`
on that server, in Prometheus' text format, and turns their collection on.
`metrics('/internal/metrics')` puts them elsewhere.

| Metrics | What they are |
|---|---|
| `cairo_http_request_duration_seconds` | A histogram of every HTTP request, by `method`, `route` and `status`. Its `_count` is the number of requests, so one metric gives the rate, the errors and the latency of each route |
| `cairo_grpc_call_duration_seconds` | The same for the gRPC calls the process serves, by `method` (`helloworld.Greeter/SayHello`) and `code` (`OK`, `NotFound`) |
| `cairo_php_threads{pool="request"}`, `{pool="offload"}` | The PHP threads |
| `cairo_php_threads_busy` | Request threads that are running PHP at this moment. Close to `cairo_php_threads` for long means the CPU is the limit, or something [blocks](blocking.md) |
| `cairo_php_requests_in_flight` | Requests that the PHP threads hold or that wait for them: with fibers, most of them are waiting on I/O |
| `cairo_php_thread_restarts_total` | Threads started again after a fatal error ([supervision](supervision.md)) |
| `cairo_php_thread_recycles_total` | Threads replaced at `maxRequests()` or `maxMemory()` |
| `go_*`, `process_*` | The Go runtime and the process: memory, CPU seconds, open files, goroutines |

```promql
sum by (route) (rate(cairo_http_request_duration_seconds_count[1m]))                 # requests per second, by route
histogram_quantile(0.95, sum by (le, route) (rate(cairo_http_request_duration_seconds_bucket[5m])))   # p95, by route
sum(rate(cairo_http_request_duration_seconds_count{status=~"5.."}[5m]))
  / sum(rate(cairo_http_request_duration_seconds_count[5m]))                         # share of errors
cairo_php_threads_busy / ignoring(pool) cairo_php_threads{pool="request"}            # how busy PHP is
```

`route` is the route as `server.php` declared it (`/orders/{id}`), never the
path of the request. A request that matched no route has an empty `route`.
An app served through `fallback()`, as a [framework](frameworks.md) is, has
the one route `/`: Cairo does not know the framework's routes.

Labels never come from what a client is free to choose. A method that is
not one of HTTP's is counted as `other`, and a gRPC call to a method that no
declared service has is not counted (nor are the built-in health and
reflection services). The buckets go from 1 ms to 10 s.

The numbers describe the whole process, on whichever server the endpoint is,
and they say a lot about an app: its routes, its traffic, its errors. Put the
endpoint on a server of its own that only your monitoring reaches, on
`127.0.0.1` or a private address, as in the example above. The endpoint, like
the probes below, is not counted in the metrics and not traced.

```yaml
# prometheus.yml
scrape_configs:
  - job_name: cairo
    static_configs:
      - targets: ['10.0.0.5:9100']
```

## Health and readiness probes

`$http->health()` answers two probes on that server without running PHP, so
they answer while every PHP thread is busy:

- `GET /healthz` is 200 for as long as the process serves. Use it as the
  liveness probe.
- `GET /readyz` is 200 once the PHP threads take requests, and 503 from the
  moment the process is told to stop. Use it as the readiness probe.

`health('/live', '/ready')` names them differently. They fit on the server
with the metrics, and on the serving port too, when the load balancer probes
there.

A Cairo server opens its ports only after `server.php` has run on every PHP
thread, which is where a framework boots, so a process that accepts
connections is ready. The other end is the one that needs care. A load
balancer keeps sending requests to a process for a moment after it was told
to stop. `--drain` covers that moment:

```sh
cairo serve server.php --drain 5s
```

On SIGTERM or SIGINT the readiness probe answers 503 at once and Cairo keeps
serving as before for 5 seconds. Then it stops accepting connections and
finishes the requests in flight ([stopping the server](supervision.md)), for
`--grace` at most. A second signal ends the wait. Without `--drain`, the
default, it stops accepting at once.

```yaml
# Kubernetes
livenessProbe:
  httpGet: { path: /healthz, port: 9100 }
readinessProbe:
  httpGet: { path: /readyz, port: 9100 }
  periodSeconds: 2
terminationGracePeriodSeconds: 40   # more than --drain plus --grace
```

In the [official image](docker.md), which has BusyBox's `wget`:

```dockerfile
HEALTHCHECK CMD wget -qO /dev/null http://127.0.0.1:9100/healthz || exit 1
```

The probes say that the process is up and takes requests, not that the app's
database is reachable. For a probe that asks PHP, declare a route of your
own and have it check what you need.

## Tracing

`$app->tracing()` makes every HTTP request and every gRPC call a span, and
sends the spans in batches to a collector with OTLP over HTTP. It is the
OpenTelemetry Go SDK, set up by Cairo.

```php
$app->tracing(service: 'orders', endpoint: 'http://otel-collector:4318', sample: 0.1);
```

Each argument can be left out, and then the standard variables of the
environment decide:

| Argument | Variable | Without both |
|---|---|---|
| `service` | `OTEL_SERVICE_NAME` | `cairo` |
| `endpoint` | `OTEL_EXPORTER_OTLP_ENDPOINT` | `https://localhost:4318` |
| `sample`, the share of traces that start here to record | `OTEL_TRACES_SAMPLER`, `OTEL_TRACES_SAMPLER_ARG` | every trace |

The endpoint is the collector's base address, to which `/v1/traces` is
added. The exporter also reads `OTEL_EXPORTER_OTLP_HEADERS`,
`OTEL_EXPORTER_OTLP_TIMEOUT`, `OTEL_EXPORTER_OTLP_CERTIFICATE` and the
`OTEL_BSP_*` settings of the batches, and `OTEL_RESOURCE_ATTRIBUTES` adds
attributes to every span. A token for a hosted collector belongs in
`OTEL_EXPORTER_OTLP_HEADERS`, not in `server.php`. A collector that cannot
be reached is logged as a warning and never holds a request up: spans wait
in a bounded queue and are dropped when it is full.

A span is named by its route, `GET /orders/{id}`, or by the gRPC method,
`helloworld.Greeter/SayHello`, and has the attributes OpenTelemetry's
conventions define: for HTTP the method, the route, the path, the status,
the protocol, the client's address and its user agent. The path and the
user agent are cut at 2048 bytes (`OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT`
changes that), the query string is left out, and so is the `Host` header.
A response of 500 or more marks the span as failed, and so does a gRPC
status that is the server's fault (`INTERNAL`, `UNAVAILABLE`,
`DEADLINE_EXCEEDED` and the like), not one that is the caller's
(`NOT_FOUND`, `INVALID_ARGUMENT`).

### Traces across services

A request that arrives with a W3C `traceparent` header continues that
trace: its span is a child of the caller's span, and is sampled if the
caller's was. Without the header a new trace starts.

From PHP, the trace goes on like this:

- Calls through `Cairo\Grpc\Client` are spans under the request that makes
  them, and carry the trace to the service they call. Nothing to do.
- For calls PHP makes itself, with curl or an HTTP client, pass the span on
  in a header:

  ```php
  $http->get('/orders/{id}', function (Request $req, Context $ctx): Response {
      $curl = curl_init('http://stock/items/' . $req->param('id'));
      curl_setopt($curl, CURLOPT_HTTPHEADER, ['traceparent: ' . $ctx->value('traceparent')]);
      // ...
  });
  ```

  `$ctx->value('traceparent')` is the request's span, in HTTP and gRPC
  handlers alike, and `null` when tracing is off.
- An app that has OpenTelemetry's PHP SDK needs nothing: the `traceparent`
  header of the request it sees is Cairo's span, so the spans the SDK makes
  (queries, cache calls, the framework's own) hang under it.

Cairo trusts the `traceparent` it is sent, as proxies and other servers do.
On a server that the internet reaches directly, a client can therefore
choose its trace id and ask for its request to be recorded, whatever
`sample` says. That costs the CPU time of a recorded span for each such
request and puts the client's spans among yours; it cannot hold requests up
or grow memory. Strip the header in the proxy or load balancer in front of
such a server. Sampling by ratio alone does not help: its decision is made
from the trace id, which the client chose.

## What it costs

Nothing when it is not declared: the handlers are then not wrapped at all.
Declared, the work is per request, in Go, and does not touch the PHP thread.

Measured on a 4-core cloud machine with the load on the same machine, as
CPU time of the Cairo process for each request (a `Hello` route, and a JSON
answer of 20 rows):

| Declared | `Hello` | JSON of 20 rows |
|---|---|---|
| Nothing | 52.7 µs | 65.5 µs |
| `metrics()` | 53.3 µs | 64.7 µs |
| `tracing(sample: 0.1)` | 60.3 µs | 74.9 µs |
| `tracing()`, every trace recorded | 68.0 µs | 82.7 µs |
| `metrics()` and `tracing()` | 70.5 µs | 85.3 µs |

The metrics cost nothing that can be measured: one histogram observation
for each request. A recorded span costs about 15 µs, most of it in
OpenTelemetry's SDK, which keeps the span and sends it. A request that is
not recorded still costs 6 to 8 µs: it gets the ids of a span, and PHP is
handed them, so that the services it calls learn that the trace is not
sampled. On a busy server, set `sample`.

`examples/observability` in the Cairo repository has all three, with a gRPC
call from PHP in one trace.

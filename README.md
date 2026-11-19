# Cairo documentation

User documentation for [Cairo](https://github.com/cairophp/cairo), a PHP
application server written in Go: you declare HTTP and gRPC servers in PHP,
and Go does the serving. Every request runs in its own PHP Fiber with its own
goroutine, so one PHP thread can hold thousands of requests at once.

These pages describe the `main` branch of Cairo;
[CHANGELOG.md](https://github.com/cairophp/cairo/blob/main/CHANGELOG.md) says
which release has what. Paths such as `examples/greeter` are in the Cairo
repository.

## Start

- [Install, supported platforms and known limitations](install.md)
- [How it works](how-it-works.md)

## Serving

- [gRPC](grpc.md)
- [Middleware](middleware.md)
- [Response cache](response-cache.md)
- [TLS](tls.md)

## Concurrency

- [Context and deadlines](context.md)
- [Concurrency API](concurrency.md)
- [Request state: Context values](context-values.md)
- [Runtime hooks](runtime-hooks.md)
- [Finding blocking code](blocking.md)
- [Slow request log](slow-requests.md)
- [Repeated queries (N+1)](repeated-queries.md)
- [Heavy routes](heavy-routes.md)

## Data and I/O

- [PostgreSQL](postgresql.md)
- [Cairo\Sql](sql.md)
- [Connection pools](pools.md)
- [HTTP client](http-client.md)
- [Cairo\Net](net.md)

## Running applications

- [Isolated mode](isolated-mode.md)
- [Frameworks: PSR-15, Symfony and Laravel](frameworks.md)
- [Amp and Revolt](revolt.md)
- [Thread supervision](supervision.md)

## Tooling

- [IDE and static analysis](ide.md)
- [Building Cairo, PHP settings and the static binary](building.md)

## Changing these pages

A user-facing change in Cairo (a new or changed `Cairo\` API, CLI flag,
install step or limitation) comes with a change here: open a pull request in
this repository and link it from the Cairo pull request.

# Cairo documentation

User documentation for [Cairo](https://github.com/cairophp/cairo), a PHP
application server written in Go: you declare HTTP and gRPC servers in PHP,
and Go does the serving. Every request runs in its own PHP Fiber, and a
fiber that waits leaves its thread to the others, so one PHP thread can hold
thousands of requests at once.

These pages describe the `main` branch of Cairo;
[CHANGELOG.md](https://github.com/cairophp/cairo/blob/main/CHANGELOG.md) says
which release has what. Paths such as `examples/greeter` are in the Cairo
repository.

## Start

- [Install, supported platforms and known limitations](install.md)
- [Docker: the official image](docker.md)
- [How it works](how-it-works.md)
- [Stability: what a release may change](stability.md)

## Serving

- [HTTPS and HTTP/2](https.md)
- [gRPC](grpc.md)
- [Middleware](middleware.md)
- [Response cache](response-cache.md)
- [Streamed answers, Server-Sent Events and files](streaming.md)
- [The Mercure hub](mercure.md)
- [TLS for outgoing connections](tls.md)

## Concurrency

- [Context and deadlines](context.md)
- [Concurrency API](concurrency.md)
- [Request state: Context values](context-values.md)
- [Request-local statics](request-local.md)
- [Runtime hooks](runtime-hooks.md)
- [Finding blocking code](blocking.md)
- [Slow request log](slow-requests.md)
- [Heavy routes](heavy-routes.md)

## Data and I/O

- [MySQL and MariaDB, and a recommended setting](mysql.md)
- [PostgreSQL](postgresql.md)
- [Connection pools](pools.md)
- [Cairo\Net](net.md)

## Running applications

- [PHP command line: artisan, bin/console and Composer on the Cairo binary](cli.md)
- [Isolated mode](isolated-mode.md)
- [Frameworks: PSR-15, Symfony and Laravel](frameworks.md)
- [Thread supervision](supervision.md)
- [Metrics, health probes and tracing](observability.md)

## Tooling

- [IDE and static analysis](ide.md)
- [Building Cairo, PHP settings and the static binary](building.md)

## Changing these pages

A user-facing change in Cairo (a new or changed `Cairo\` API, CLI flag,
install step or limitation) comes with a change here: open a pull request in
this repository and link it from the Cairo pull request.

These pages are also the website. `site/build.py` turns them into the landing
page and the docs site, and `.github/workflows/site.yml` publishes the result
with GitHub Pages on every push to `main`. A page appears there once it is in
the lists above. To build the site yourself:

```sh
pip install -r site/requirements.txt
python3 site/build.py .        # writes site/out/pages/
```

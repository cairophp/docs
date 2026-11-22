# Install

Cairo ships as one static binary for Linux on amd64 and arm64, with PHP 8.5,
opcache and the extensions built in. Nothing else is needed at run time, not even
libc, so it also runs in `FROM scratch` images. Download it from the
[releases page](https://github.com/cairophp/cairo/releases) and check
it against `SHA256SUMS`:

```sh
curl -fsSLO https://github.com/cairophp/cairo/releases/download/v0.2.0/cairo-linux-amd64
curl -fsSLO https://github.com/cairophp/cairo/releases/download/v0.2.0/SHA256SUMS
sha256sum --check --ignore-missing SHA256SUMS
install -m 755 cairo-linux-amd64 /usr/local/bin/cairo
cairo version
```

While the repository is private, download with `gh release download v0.2.0`
instead. In a container:

```dockerfile
FROM scratch
COPY cairo-linux-amd64 /cairo
COPY . /app
WORKDIR /app
ENTRYPOINT ["/cairo", "serve", "server.php"]
```

To build it yourself, see [Building](building.md). For your IDE and PHPStan, add
the stubs package ([IDE and static analysis](ide.md)).

## Supported platforms

- Linux on amd64 and arm64. macOS and Windows are not supported, since Cairo
  relies on a thread-safe PHP embedded in a Go process; use the binary in
  Docker there.
- PHP 8.1 or newer when you build Cairo yourself; the release binary has
  PHP 8.5.
- PostgreSQL (`pdo_pgsql`, through pgx) and MySQL or MariaDB (PDO MySQL and
  mysqli through hooked streams).

## Known limitations

- **Fiber safety.** Requests on a thread share globals and static properties.
  In the default fiber mode, keep request state on `Request` and `Context`;
  Cairo does not fill `$_GET`, `$_POST` or `$_SERVER`. Run code that relies on
  them, or on per-request singletons, with `->concurrency('isolated')`.
- **Blocking extensions.** Only what the runtime hooks cover suspends a
  fiber: sleep, PHP streams and sockets, DNS, curl, and `pgsql:`. Other C
  extensions that open their own sockets (the MongoDB driver, gRPC's C
  extension, libmysqlclient builds) block the whole thread;
  `App::detectBlocking()` finds them.
- **Extensions.** The release binary has a fixed set of extensions
  ([Building](building.md)) and cannot load others (`dl()` is off). phpredis,
  imagick, mongodb and other PECL extensions are not included; build Cairo
  yourself to add them, as long as they are thread-safe under ZTS.
- **One process.** Cairo runs one process with many PHP threads; it does not
  fork. A fatal error in PHP kills only its thread, which is replaced, but a
  crash in C code takes the process down: run it under a supervisor
  (systemd, Kubernetes) that restarts it.
- **Not included:** HTTP/3, automatic TLS certificates, and a file watcher
  for development reloads.

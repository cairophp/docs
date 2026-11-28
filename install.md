# Install

Cairo ships as one static binary for Linux on amd64 and arm64, with PHP,
opcache and the extensions built in. There is one binary for each PHP that
Cairo supports, 8.3, 8.4, 8.5 and 8.6, and the default has the newest. Nothing else is needed at run time, not even
libc. This installs the latest release into `/usr/local/bin`:

```sh
curl -fsSL https://raw.githubusercontent.com/cairophp/cairo/main/install.sh | bash
cairo version
```

The binary contains the [Mercure hub](mercure.md), which is licensed under
the AGPL-3.0 and not, like Cairo, under Apache-2.0;
[a binary without it](mercure.md#a-binary-without-the-hub) is built from
source.

The script picks the binary for your machine and checks it against the
release's `SHA256SUMS` before it installs anything. `CAIRO_PHP=8.4` picks
the binary with PHP 8.4, `CAIRO_VERSION=v0.8.0` a release and
`CAIRO_INSTALL_DIR` another directory:

```sh
curl -fsSL https://raw.githubusercontent.com/cairophp/cairo/main/install.sh | CAIRO_PHP=8.4 bash
```

The binaries are named for their PHP, `cairo-php8.4-linux-amd64`, and the
newest PHP's is also `cairo-linux-amd64`. Releases up to 0.6.0 have one
binary, with PHP 8.5, under the plain name only. `CAIRO_LIBC=gnu` installs
the glibc binary instead, which loads extensions, with the kit to build them
([the glibc binary](extensions.md#the-glibc-binary)). To do the same by
hand, download from the
[releases page](https://github.com/cairophp/cairo/releases):

```sh
curl -fsSLO https://github.com/cairophp/cairo/releases/download/v0.8.0/cairo-linux-amd64
curl -fsSLO https://github.com/cairophp/cairo/releases/download/v0.8.0/SHA256SUMS
sha256sum --check --ignore-missing SHA256SUMS
install -m 755 cairo-linux-amd64 /usr/local/bin/cairo
```

In a container, use the official image ([Docker](docker.md)):

```dockerfile
FROM ghcr.io/cairophp/cairo:0.8
COPY --chown=cairo:cairo . /app
```

The binary is PHP's command line too: `cairo php artisan migrate` runs a
script with the PHP inside it ([PHP command line](cli.md)).

To build it yourself, see [Building](building.md). For your IDE and PHPStan, add
the stubs package ([IDE and static analysis](ide.md)).

## Supported platforms

- Linux on amd64 and arm64. macOS and Windows are not supported, since Cairo
  relies on a thread-safe PHP embedded in a Go process; use the
  [official image](docker.md#macos-and-windows) in Docker there.
- PHP 8.3, 8.4, 8.5 or 8.6 in the release binaries and images (8.6 by
  default), and PHP 8.1 or newer when you build Cairo yourself. With PHP 8.3
  the server [cannot see opcache's restart coming](supervision.md#when-opcache-has-to-restart)
  and the threads of a [reload](reload.md) do not use opcache: prefer 8.4 or
  newer.
- PostgreSQL (PHP's `pdo_pgsql`, on libpq) and MySQL or MariaDB (PDO MySQL and
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
- **Extensions.** The default release binary has a fixed set of extensions
  ([Building](building.md)) and cannot load others (`dl()` is off). For
  phpredis, imagick, mongodb and other PECL extensions, use the glibc binary
  or the native image, which load them, or build a static binary with them
  ([Adding PHP extensions](extensions.md)); they must be thread-safe. `pcntl`
  is there for the scripts of `cairo php` only, without `pcntl_fork()`
  ([signals](cli.md#signals)).
- **One process.** Cairo runs one process with many PHP threads; it does not
  fork. A fatal error in PHP kills only its thread, which is replaced, but a
  crash in C code takes the process down: run it under a supervisor
  (systemd, Kubernetes) that restarts it.
- **Not included:** HTTP/3 and response compression.

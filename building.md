# Building

Cairo links against a thread-safe (ZTS) libphp, built with `--enable-embed`
for the library, and runs PHP as its own SAPI: `PHP_SAPI` is `cairo`.

```sh
make php            # builds PHP 8.3 (ZTS, embed) into /opt/php-zts
make build          # bin/cairo
make test           # unit + end-to-end tests (set CAIRO_TEST_MYSQL to include PDO MySQL)
make run            # serves examples/greeter
```

Or with Docker: `docker build -t cairo . && docker run -p 8080:8080 -p 9000:9000 cairo`.

`make php` builds PHP with opcache and the extensions most applications
expect: mbstring, intl, openssl, sodium, zip, gd (JPEG, WebP, FreeType), bcmath,
gmp, calendar, exif, sockets, pcntl ([for scripts](cli.md#signals)), iconv, zlib, bz2, curl, PDO with MySQL and SQLite,
mysqli, sqlite3, and PHP's defaults (ctype, dom, fileinfo, filter, json,
session, simplexml, tokenizer, xml and the rest). `scripts/build-php.sh` lists
the system packages they need.

Opcache is loaded as a Zend extension at startup, so scripts are compiled once
per process and shared by all PHP threads. It does not accept the cairo SAPI by
name, so Cairo presents itself under another name only while opcache starts;
`PHP_SAPI` is still `cairo`. Its usual ini settings apply, and `CAIRO_OPCACHE=0`
leaves it out.

PHP settings come from a php.ini: `cairo serve --php-ini FILE` (or
`CAIRO_PHP_INI`, or `PHPRC`), otherwise PHP's own search, never the current
directory. Without one, errors are logged and not displayed. PHP's log lines
(errors, warnings, `error_log()`) go to Cairo's logger with `source=php`,
unless `error_log` names a file. `max_execution_time` and `max_input_time`
stay off whatever the ini says, because each PHP thread runs one long request;
request deadlines come from `Middleware::timeout()` and gRPC deadlines. `dl()`
is not available. One setting is worth adding for apps that use MySQL:
[`mysqlnd.collect_statistics = 0`](mysql.md#recommended-turn-off-mysqlnds-statistics).

Requirements: Go 1.27+, a C toolchain, the -dev packages listed in `scripts/build-php.sh`, and PHP 8.1 or newer (fibers).

## One static binary

```sh
make static         # docker build -f Dockerfile.static --output dist .
./dist/cairo serve server.php
```

`dist/cairo` holds Cairo, PHP and every extension above, linked against musl
with no shared libraries, so it runs on any Linux of the same CPU
architecture, including `FROM scratch` images. It uses PHP 8.6 with opcache
built in; pass `--build-arg PHP_VERSION=8.4.28` for another PHP, 8.3 or newer.
Before PHP 8.5 opcache can only be built as a shared extension, which a
static binary cannot load, so the build patches PHP to build it in, with
[static-php-cli](https://github.com/crazywhalecc/static-php-cli)'s patches,
and leaves its JIT out. CI builds it with each PHP that the releases ship and
runs the end-to-end tests against each.
`scripts/build-static.sh` does the work and also runs outside Docker on Alpine.
The binary cannot load extensions at run time, but a build can add more
([a static binary with more extensions](extensions.md#a-static-binary-with-more-extensions)).
`docker build -f Dockerfile.gnu --output dist .` builds the same binary on
Debian 12 with glibc left shared, which loads extensions, and the kit to
build them, `dist/cairo-dev.tar.gz` ([the glibc binary](extensions.md#the-glibc-binary)).
Both builds link in the [Mercure hub](mercure.md), which is AGPL-3.0;
`make build TAGS=nomercure` and `--build-arg CAIRO_TAGS=nomercure`
[leave it out](mercure.md#a-binary-without-the-hub).
The first build takes about 15 minutes, nearly all of it ICU and PHP. Docker
keeps those in their own layer, so later builds only compile Cairo, until
`PHP_VERSION` or the script changes. Outside Docker, set `WORK` to a fixed
directory for the same effect.

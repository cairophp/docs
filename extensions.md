# Adding PHP extensions

The default release binary has a fixed set of extensions
([Building](building.md)). It cannot load more at run time: it is a static
program, and a static program on musl has no `dlopen()`. There are three
ways to give an app the extensions it needs, each with PHP's own tools:

| | The native image | The glibc binary | A static binary of your own |
|---|---|---|---|
| What it is | Cairo built against the official `php` image's own PHP | The release binary, linked against glibc, which loads extensions | The static binary with more extensions built in |
| How you add one | `docker-php-ext-install`, `pecl install` or `install-php-extensions` in your Dockerfile, as for any `php` image | `phpize`, `./configure`, `make install` with its kit | Build arguments, then one build |
| Runs on | Docker (Debian trixie) | Any Linux with glibc 2.36 or newer | Any Linux, `FROM scratch` too |
| Extensions | Shared (`.so`), loaded at start like PHP's | Shared (`.so`), loaded at start like PHP's | Linked in |

Pick the native image when the app needs extensions and runs in a
container. Pick the glibc binary on a server or VM, or in an image of your
own. Pick a static binary of your own when it must be one file with no libc.

Whichever you use, an extension must build for the PHP version (a PECL
release says which it supports) and be thread-safe: Cairo runs PHP in
threads. An extension that opens its own sockets (phpredis, the MongoDB
driver) blocks the PHP thread while it waits, in fiber mode
([blocking extensions](install.md#known-limitations)).

## The native image

`ghcr.io/cairophp/cairo` with `-trixie` behind the tag is Cairo built against
the official [`php`](https://hub.docker.com/_/php) image of the same PHP:
`php:8.4-zts-trixie` for PHP 8.4, `php:8.6-cli-trixie` for 8.6 (8.6's images
are thread-safe). Its PHP, its php.ini directory and its tools are the `php`
image's, so an extension goes in the way the `php` image documents:

```dockerfile
FROM ghcr.io/cairophp/cairo:0.6-php8.5-trixie
USER root
RUN docker-php-ext-install pdo_pgsql intl \
    && pecl install redis \
    && docker-php-ext-enable redis
USER cairo
COPY --chown=cairo:cairo . /app
```

Installing needs root, and the image runs as `cairo` (uid 1000): switch to
root for it and back. `cairo php -m` lists what is loaded, and the server's
threads load the same.

| Tag | What it follows |
|---|---|
| `0.6.1-php8.4-trixie` | That release with PHP 8.4, never moved |
| `0.6-php8.4-trixie` | The newest `0.6.x` with PHP 8.4 |
| `php8.4-trixie` | The newest release with PHP 8.4 |
| `0.6-trixie`, `trixie` | The same, with the newest PHP |

The same goes for `php8.3`, `php8.5` and `php8.6`. The image starts as the
Alpine one does ([Docker](docker.md#an-image-for-your-app)): it runs
`cairo serve server.php` in `/app`, as the user `cairo`. `php` in it is the
`php` image's own command line, not Cairo's: run the app's commands with
`cairo php`, as in `docker run --rm my-app php artisan migrate`, where `php`
is the argument that the image's `cairo` takes.

The `php` image has fewer extensions than the release binary. It has
opcache (Cairo loads it), curl, openssl, sodium and PDO with SQLite, but not
mbstring, intl, gd, zip, bcmath, pcntl, mysqli or the PDO drivers for MySQL
and PostgreSQL until you add them. `cairo php -m` lists what yours has.

## The glibc binary

Each release has, next to the static binaries, one for glibc of each PHP
and architecture: `cairo-php8.5-linux-amd64-gnu` and so on, and
`cairo-linux-amd64-gnu` with the newest PHP. It has the same PHP and the same
extensions as the static binary, and it is static too except for glibc, which
it uses from the system: that is what lets it load an extension. It needs
glibc 2.36 or newer (Debian 12, Ubuntu 24.04, RHEL 10 and the distributions
of their time), and runs on any of them.

An extension must be built for exactly that PHP, so the release has a kit
next to each glibc binary, `cairo-php8.5-linux-amd64-gnu-dev.tar.gz`: that
PHP's headers, `php-config` and `phpize`, unpacked in `/opt/cairo/php8.5`.
`install.sh` installs both:

```sh
curl -fsSL https://raw.githubusercontent.com/cairophp/cairo/main/install.sh | CAIRO_LIBC=gnu CAIRO_PHP=8.5 bash
```

Then build the extension from its sources, as for any PHP, with the kit's
`phpize` and `php-config` (the build needs a C compiler and autoconf):

```sh
curl -fsSL https://pecl.php.net/get/redis | tar -xz && cd redis-*/
/opt/cairo/php8.5/bin/phpize
./configure --with-php-config=/opt/cairo/php8.5/bin/php-config
make && sudo make install       # into /opt/cairo/php8.5/lib/php/extensions/...
cairo php -d extension=redis -m | grep redis
```

`make install` puts the `.so` in the kit's extension directory, where
`extension=redis` finds it by name; an absolute path works from anywhere.
To load it everywhere, in servers and in `cairo php`, put `extension=redis`
in `/opt/cairo/php8.5/lib/php.ini`, the php.ini the binary reads when none
is named. Another one goes with `--php-ini` or `CAIRO_PHP_INI`
([PHP settings](building.md)). The binary never reads the system PHP's
php.ini.

A library that the extension links (imagick's ImageMagick, for example) is
the system's, as for any extension. One that the binary has inside it too,
such as OpenSSL or libxml2, is the binary's for the extension as well: an
extension built against another major version of it may fail. CI builds
the glibc binary of each PHP and architecture, builds shmop with its kit,
and loads it in `cairo php` and in a server.

## A static binary with more extensions

`Dockerfile.static` in the Cairo repository takes three build arguments:

| Argument | What it adds |
|---|---|
| `EXTRA_EXTENSIONS` | Flags for PHP's `configure`: PHP's own extensions that are off by default (`--enable-shmop`, `--with-xsl`), and the flag of each PECL package below |
| `PECL_EXTENSIONS` | PECL packages as `name-version` (`apcu-5.1.28`), fetched from pecl.php.net into PHP's sources and built in |
| `APK_PACKAGES` | Alpine packages the build needs for them: the `-dev` and `-static` packages of their libraries |

```sh
git clone https://github.com/cairophp/cairo && cd cairo
docker build -f Dockerfile.static --output dist \
  --build-arg PHP_VERSION=8.5.13 \
  --build-arg PECL_EXTENSIONS="apcu-5.1.28" \
  --build-arg EXTRA_EXTENSIONS="--enable-apcu --enable-shmop" .
./dist/cairo php -m
```

A PECL package is built in, so it needs the version that builds with that
PHP; APCu 5.1.28, the newest, does not build with PHP 8.6 yet. A library it
links must have a static version on Alpine. CI builds a binary with APCu and
shmop and uses both.

`dist/cairo` is then a binary like the release's, with your extensions in it:
put it in your image as the official image does (`COPY dist/cairo
/usr/local/bin/cairo` on Alpine, or `FROM scratch`).

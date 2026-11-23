# Docker

The official image is `ghcr.io/cairophp/cairo`, for amd64 and arm64. It is
the release's static binary on Alpine, and nothing else: PHP 8.5, opcache and
the extensions are inside the binary
([what the release binary has](building.md)).

| Tag | What it follows |
|---|---|
| `0.5.0` | That release, never moved |
| `0.5` | The newest `0.5.x` |
| `latest` | The newest release |

Before 1.0 a minor version may change the PHP API ([Stability](stability.md)),
so build on `0.5`, not on `latest`.

## An image for your app

```dockerfile
FROM ghcr.io/cairophp/cairo:0.5
COPY --chown=cairo:cairo . /app
```

```sh
docker build -t my-app .
docker run -p 8080:8080 my-app
```

The image's working directory is `/app` and it runs `cairo serve server.php`
there. Make `server.php` listen on all interfaces (`$app->http(':8080')`), not
on `127.0.0.1`, or the published port reaches nothing. To serve another file
or pass flags, give the command: `docker run my-app serve app/server.php
--threads 4`. `docker run ghcr.io/cairophp/cairo:0.5 version` prints the
version.

The process runs as the user `cairo` (uid 1000), not as root. Copy your files
with `--chown=cairo:cairo` when the app writes to its own directory (logs, a
cache, uploads), and mount volumes that uid 1000 may write to. A port below
1024 needs `USER root` in your Dockerfile; publishing `-p 80:8080` does not.

Install Composer packages in a build stage and copy `vendor/` over, since the
image has no Composer and no `php` command:

```dockerfile
FROM composer:2 AS vendor
WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-scripts --prefer-dist

FROM ghcr.io/cairophp/cairo:0.5
COPY --chown=cairo:cairo . /app
COPY --from=vendor --chown=cairo:cairo /app/vendor /app/vendor
```

Cairo stops gracefully on `SIGTERM`, which is what `docker stop` and
Kubernetes send: it finishes the requests in flight for up to `--grace`
(30 s). Give the container at least that long (`docker stop -t 35`,
`terminationGracePeriodSeconds`).

## When you need the `php` command too

The image has no PHP CLI, so it cannot run `php artisan`, `bin/console` or
Composer scripts. Where the app needs them (Laravel through Octane starts
with `php artisan octane:start`), start from a PHP image and copy the binary
in. It is static, so it runs on any Linux image:

```dockerfile
FROM php:8.5-cli
COPY --from=ghcr.io/cairophp/cairo:0.5 /usr/local/bin/cairo /usr/local/bin/cairo
```

Keep that image's PHP at the version inside Cairo (8.5 for the release
binary), so that the commands and the server agree on what the code may use.

## macOS and Windows

Cairo runs on Linux only ([supported platforms](install.md#supported-platforms)).
On macOS and Windows, develop in Docker with your project mounted:

```sh
docker run --rm -it -p 8080:8080 -v "$PWD":/app ghcr.io/cairophp/cairo:0.5
```

Docker Desktop runs the arm64 image on Apple silicon and the amd64 image on
Intel machines. Cairo keeps your code in memory, so restart the container
after you change a file.

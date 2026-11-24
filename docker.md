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

The image is also PHP's command line ([PHP command line](cli.md)): the
binary runs scripts as `cairo php`, and `/usr/local/bin/php` is a link to it.
So the commands of your app run in the same image as the app:

```sh
docker run --rm my-app php artisan migrate --force      # runs: cairo php artisan migrate --force
docker run --rm my-app php bin/console cache:warmup
```

In Kubernetes that is an init container or a Job with
`args: ["php", "artisan", "migrate", "--force"]`, and a queue worker is a
Deployment of the same image with `args: ["php", "artisan", "queue:work"]`.

Install Composer packages when you build the image. Composer is a PHP
script, so it runs on the image as well, with the extensions the app will
have:

```dockerfile
FROM ghcr.io/cairophp/cairo:0.5
COPY --from=composer:2 /usr/bin/composer /usr/local/bin/composer
COPY --chown=cairo:cairo . /app
RUN php /usr/local/bin/composer install --no-dev --prefer-dist
```

Composer unpacks archives with PHP's zip extension here, since Alpine has no
`unzip` and no `git` until you add them (`USER root`, `apk add --no-cache git
unzip`, `USER cairo`). To keep Composer out of the final image, install in a
build stage and copy `vendor/` over:

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

A CPU limit (`docker run --cpus=2`, a limit in Kubernetes) does not set the
number of PHP threads: Cairo starts one for each CPU of the machine, and
as many for `offload()`, unless you say how many (`$app->threads(4)`,
`$app->offloadThreads(2)`, or `--threads` and `--offload-threads`). On a
large machine with a small limit, say it, or the threads share the little
CPU time the limit gives. Go's side of Cairo counts the CPUs of the limit
itself.

## Laravel in the image

Laravel runs on Cairo through Octane and the
[Cairo driver](https://github.com/cairophp/octane). Octane's own start
command, `php artisan octane:start`, runs on the binary too, but it is a
second process that starts Cairo and passes signals on. In the image, start
the server file that the command would start, with its settings in the
environment:

```dockerfile
FROM ghcr.io/cairophp/cairo:0.5
COPY --chown=cairo:cairo . /app
ENV LARAVEL_OCTANE=1 \
    APP_BASE_PATH=/app \
    CAIRO_OCTANE_HOST=0.0.0.0 \
    CAIRO_OCTANE_PORT=8080 \
    CAIRO_OCTANE_PUBLIC_PATH=/app/public
CMD ["serve", "vendor/cairophp/laravel-octane/bin/cairo-worker.php"]
```

`CAIRO_OCTANE_MODE=fibers`, `CAIRO_OCTANE_CONCURRENCY`, `CAIRO_OCTANE_WORKERS`
and `CAIRO_OCTANE_MAX_REQUESTS` are the command's `--mode`, `--concurrency`,
`--workers` and `--max-requests`. Cairo is then the container's own process,
so `docker stop` reaches it without a command in between. Migrations, queue
workers and the scheduler run from the same image:

```sh
docker run --rm my-app php artisan migrate --force
docker run -d my-app php artisan queue:work
docker run -d my-app php artisan schedule:work
```

## macOS and Windows

Cairo runs on Linux only ([supported platforms](install.md#supported-platforms)).
On macOS and Windows, develop in Docker with your project mounted:

```sh
docker run --rm -it -p 8080:8080 -v "$PWD":/app ghcr.io/cairophp/cairo:0.5
```

Docker Desktop runs the arm64 image on Apple silicon and the amd64 image on
Intel machines. Cairo keeps your code in memory, so restart the container
after you change a file.

# Classic mode: WordPress and other script apps

Apps that are a set of PHP scripts (WordPress, Drupal, phpMyAdmin, a folder of
`.php` files) expect what PHP-FPM gives them: a fresh PHP request for every
HTTP request, in which they load their files, define their functions and
constants and keep their state in globals. Classic mode gives them that:

```php
<?php // server.php

$app = (new Cairo\App())
    ->concurrency('classic')
    ->threads(8);

$app->http(':8080')->scripts(__DIR__ . '/wordpress');

return $app;
```

```sh
cairo serve server.php
```

`scripts($dir)` does what nginx's `try_files` and `fastcgi_split_path_info`
do in front of PHP-FPM:

| Request | What answers it |
|---|---|
| `/wp-login.php` | the script `wp-login.php` |
| `/index.php/some/path` | `index.php`, with `PATH_INFO` = `/some/path` |
| `/wp-admin/` | `wp-admin/index.php` |
| `/wp-admin` | a 301 to `/wp-admin/` |
| `/wp-content/themes/x/style.css` | the file, served by Go (as `publicDir()`) |
| `/2026/11/hello-world/`, any other path | the front controller `index.php` (WordPress' pretty links) |
| `/.env`, `/.git/config`, any hidden path | the front controller: hidden files are never served |

Without an `index.php` at the root, a path that names no script and no file
is a 404. A PHP file is never sent as a file, and every lookup stays inside
the directory, symlinks included.

## Serving with no declaration

A folder, or a PHP file that declares no `Cairo\App`, needs no server.php:
`cairo serve` serves it as nginx and PHP-FPM do, in classic mode.

```sh
cairo serve wordpress/                       # a folder: the table above
cairo serve public/index.php --listen :80    # a front controller: Laravel, Slim, your own
```

| You give | What answers |
|---|---|
| a folder | the table above, with the folder as the document root |
| a plain PHP file | the same, with the file's folder as the root and the file as the front controller |
| a file that names `Cairo\App` (`new App()`, `use Cairo\App;`) | what the file declares, in the mode it declares |
| a Symfony front controller with `cairophp/symfony-runtime` chosen | what the runtime declares |

Cairo reads the file with PHP's tokenizer to tell which it is, and never runs
it to find out. The settings come from the command line: `--listen` (default
`:8080`), `--threads` (default: one per CPU core; size it as you would
`pm.max_children`), `--timeout` (a request's deadline, as
`Middleware::timeout()` below), `--php-ini`, `--watch`. Without
`--timeout`, php.ini's `max_execution_time` is the deadline, as under
PHP-FPM, but in wall time (PHP-FPM counts CPU time on Linux), and
`set_time_limit()` does not change it. With neither, a request has no
deadline.

Nothing of the app runs before a request: each request runs only its script,
so every request behaves the same, as under PHP-FPM. A setting that every
script needs goes in php.ini, or in a file that php.ini's `auto_prepend_file`
names. Apart from the deadline, there is no Go middleware without a declaration.
Cairo's concurrency API (`Cairo\async()`, `await()`, `select()`,
`Cairo\sleep()`, `offload()`, `Cairo\Pool`) works in such a script as in a
declared one, and the rest of Cairo's runtime loads only when a script uses it.

## What a script gets

As under PHP-FPM:

- `$_GET`, `$_POST`, `$_FILES`, `$_COOKIE`, `$_REQUEST` and `$_SERVER`, with
  `SCRIPT_FILENAME`, `SCRIPT_NAME`, `PHP_SELF`, `PATH_INFO`, `DOCUMENT_ROOT`,
  `SERVER_PORT`, `HTTP_HOST` and the request's headers; `php://input` is the
  request's body.
- The script runs in the global scope, in its own directory, with
  `auto_prepend_file` and `auto_append_file`. `exit()` ends the script, and
  the functions it registered with `register_shutdown_function()` run before
  the request is answered.
- What it echoes, its `header()`, `setcookie()` and `http_response_code()` are
  the answer. `flush()` sends what was echoed so far, and
  `fastcgi_finish_request()` works ([Streamed answers](streaming.md)).
- PHP's own sessions (`session_start()`), one per request.
- The environment functions work as under PHP-FPM. The request's CGI
  variables (`REQUEST_METHOD`, `REMOTE_ADDR`, `HTTP_HOST` and the other
  headers, `SCRIPT_FILENAME`, ...) are its environment: `getenv()` finds them
  first, `getenv()` with no name and `$_ENV` list them, and a change the
  script makes to `$_SERVER` does not change them. Then come what the
  request set with `putenv()` and the process's environment.
  `getenv($name, true)` skips the CGI variables.
- `putenv()` changes the request's own environment: no other request sees
  it, on its thread or another. The process's environment is only read:
  PHP's `putenv()` would write it while other threads read it, which crashes
  the process (Laravel's `.env` loader calls it on every request). This is
  the one difference from PHP-FPM, where each worker is a process of its
  own: C libraries that read the environment themselves (libpq, curl's proxy
  settings) do not see a `putenv()`.
- `$_SERVER` holds the request's variables, not the process's environment,
  as under PHP-FPM's default `clear_env = yes`; read the environment with
  `getenv()`.
- A fatal error ends that request only: the client gets a 500 and the thread
  takes the next request in a fresh PHP request.

The script runs on its thread's own stack, not in a fiber, as it does under
PHP-FPM: its own waits (PDO, curl, `sleep()`, streams) hold the thread, as
they would hold a PHP-FPM worker. The request's deadline
(`Middleware::timeout()`) still stops the script: one that computes, and one
that waits on a socket (PDO MySQL, streams) or in `sleep()`, which then throws
`Cairo\Context\DeadlineExceeded`, so a stuck query does not keep its thread
from the requests behind it. A wait inside curl or PDO PostgreSQL in the
script itself is not cut short. Cairo's concurrency API still works there: `Cairo\async()` runs a
function in a fiber of the request, whose waits overlap, and `await()`,
channels, `select()`, `offload()` and `Cairo\sleep()` let those fibers run
while the script waits ([Concurrency API](concurrency.md)).

## Database connections

Each request is a new PHP request, so a script that connects to its
database opens a new connection for every request, as it does under
PHP-FPM. A persistent connection stays with the thread from one request to
the next:

```php
$pdo = new PDO($dsn, $user, $password, [PDO::ATTR_PERSISTENT => true]);
```

On a request that runs two MySQL queries this took the CPU time per request
from 757 to 630 µs (about 20% more requests a second); PHP-FPM gains about
as much. A persistent connection is one per thread, so the database sees
up to `threads()` connections, and what a request leaves on it (an open
transaction, a lock, session variables) is there for the next request on
that thread: end transactions in the script.

## Threads

A PHP thread runs one request at a time, as a PHP-FPM worker does, so
`threads()` is the number of requests served at once: size it as you would
`pm.max_children`. Requests that arrive while every thread is busy wait in
Go, in one first-in, first-out queue. Turn on opcache (it is on in the
official image): each request loads the app's files again, as under PHP-FPM.

Each request starts a PHP request on the same system thread, which keeps its
PHP resources: starting a new thread for each request would cost about four
times the request itself.

## WordPress

WordPress 6.8 installs and runs in classic mode: the installer, the home
page, posts, comments, search and feeds, logging in, the dashboard and its
settings, pretty permalinks, the REST API, media uploads and wp-cron. Put
`server.php` next to the `wordpress` directory, as above, and set
`DB_HOST` in `wp-config.php` to your database. Set `WP_HOME` and
`WP_SITEURL` if WordPress runs behind a proxy.

Its home page and a post, on the same machine (2 cores for the server, 4 PHP
workers each, the same `php.ini` with opcache, 16 connections, 5 alternating
rounds of 8 s):

| | Cairo classic | FrankenPHP (`php_server`) | nginx + PHP-FPM |
|---|---|---|---|
| home page | 65.4 req/s | 67.0 | 72.5 |
| a post | 54.8 req/s | 57.6 | 61.1 |

PHP-FPM runs a PHP built without thread safety (NTS), which a threaded server
such as Cairo or FrankenPHP cannot use; that is likely part of its lead, but
it was not measured apart.

## Classic, isolated or fibers

- **Classic**: every request is a new PHP request. For script apps. The
  slowest of the three, as PHP-FPM is, because every request loads the app.
- **[Isolated](isolated-mode.md)**: a PHP thread boots the app once and runs
  its requests one after another. For apps with a front controller that keep
  state in globals (Laravel through Octane, Symfony).
- **Fibers** (the default): a thread runs many requests at once. For apps
  whose code keeps no request state in statics and globals.

# PHP command line

The Cairo binary is also PHP's command line, so a machine or an image with
Cairo needs no second PHP for `artisan`, `bin/console`, Composer or a script
of your own:

```sh
cairo php artisan migrate --force
cairo php bin/console cache:clear
cairo php composer.phar install --no-dev
cairo php -r 'echo PHP_VERSION, "\n";'
```

It is the PHP inside the binary, with the same version, extensions and
settings as the server: what a command can use, a request can. PostgreSQL
goes through [Cairo's own PDO driver](postgresql.md) here too.

## What a script gets

A script runs as it does under `php`:

- `PHP_SAPI` is `cli`, which is what frameworks ask to know they run in a
  terminal (`runningInConsole()` in Laravel).
- `$argv` and `$argc` start at the script; `STDIN`, `STDOUT` and `STDERR` are
  there; output is not buffered; errors are shown; there is no time limit.
- The exit status is the script's: `exit(3)` ends the command with 3, and an
  uncaught exception or a fatal error with 255.
- A first line that starts with `#!` is skipped.
- The `Cairo\` classes exist, so code shared with the server loads. No
  server and no scheduler runs: `sleep()`, sockets and queries block the
  script as they do in PHP, also inside a Fiber the script made itself.

Cairo's concurrency API works without the scheduler where it can:
`Cairo\async()` runs its task to the end before it returns, so `await()` and
`all()` have their results; `offload()` runs the job in place; `Cairo\sleep()`
blocks. A command therefore runs one after the other what a request runs at
the same time, and code that both share works in both. A `Channel` that has
to wait for another fiber throws a `LogicException`.

## Options

`cairo php -h` lists them. They are PHP's own:

| Option | What it does |
|---|---|
| `<file> [args...]`, `-f <file>` | Runs the file |
| `-r <code>` | Runs the code, without `<?php` tags |
| no file, or `--` | Runs the script it reads from standard input |
| `-d name[=value]` | Sets an INI entry; `-d name` turns it on |
| `-c <path>` | Looks for `php.ini` in this directory, or reads this file |
| `-n` | Reads no `php.ini` |
| `-l <file>...` | Checks the syntax only; the status is 255 when a file has an error |
| `-v`, `-m`, `-i`, `--ini`, `--ri <name>` | The version, the modules, `phpinfo()`, the `php.ini` files in use, one extension's settings |

Options come before the script, and what follows the script goes to it. Put
`--` before arguments that start with a dash when there is no script
(`cairo php -r 'var_dump($argv);' -- -v`).

`php.ini` is found as for the server ([PHP settings](building.md)):
`CAIRO_PHP_INI`, then `PHPRC`, then PHP's own search. A file named
`php-cli.ini` is preferred over `php.ini` by the command line only, as with
PHP.

Not there: the interactive shell (`-a`), the built-in web server (`-S`; use
`cairo serve`), and `-B`, `-R`, `-F`, `-E`, `-s` and `-w`.

## The name `php`

Tools and scripts call `php` by name: a script's first line
(`#!/usr/bin/env php`), a Composer script (`"php artisan optimize"`), a cron
entry. Give the binary that name with a link, and it is PHP's command line
whatever its arguments:

```sh
ln -s /usr/local/bin/cairo /usr/local/bin/php
php artisan queue:work
```

The [official image](docker.md) has this link.

PHP code that starts PHP again does not need it. `PHP_BINARY` is the Cairo
binary, and the binary runs a script when its first argument is a file or one
of PHP's options, so Laravel's scheduler, `@php` in Composer scripts and
Symfony's `Process` with `PhpExecutableFinder` work as they are:

```sh
/usr/local/bin/cairo artisan schedule:finish ...     # what the scheduler starts
/usr/local/bin/cairo -d memory_limit=-1 artisan package:discover
```

`serve`, `php`, `gen`, `version` and `help` are always Cairo's own commands,
also next to a file of that name.

## Queue workers and other long commands

A worker is a script like any other: `cairo php artisan queue:work`,
`cairo php bin/console messenger:consume`, `cairo php artisan schedule:work`.
One process runs one worker; start as many as you need under your supervisor
(systemd, Kubernetes, Supervisor), as with PHP.

The binary has no `pcntl` extension, so a script cannot handle signals:

- `SIGTERM` and `SIGINT` end the command at once, in the middle of a job
  too. Laravel releases such a job again after the queue's `retry_after`.
  To stop workers between jobs, use `artisan queue:restart`
  (`messenger:stop-workers` in Symfony), or let them end by themselves with
  `--max-jobs` and `--max-time`.
- A worker does not enforce a job's `--timeout`.
- Packages that require `ext-pcntl`, such as Laravel Horizon, do not install.

When you [build Cairo yourself](building.md), do not add `pcntl`: Go's
runtime owns the process's signals and threads, and PHP's handlers and
`pcntl_fork()` are not safe next to it.

## Starting up

A command starts in about the time of `php` plus the start of the Cairo
binary: on the machine these pages were measured on, `cairo php -r ''` took
35 ms against 20 ms for the PHP 8.5 command line. Opcache follows
`opcache.enable_cli`, which is off unless your `php.ini` turns it on.

`examples/cli` in the Cairo repository has a command that reads its
arguments, standard input and a database.

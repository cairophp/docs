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
- The `Cairo\` classes exist, and the script runs under Cairo's scheduler,
  as a request does. No server starts.

## Concurrency in a script

Any script that `cairo php` runs can use what a request uses:
[`async()`, `await()`, channels and `select()`](concurrency.md),
[contexts with a deadline](context.md) and the waits that suspend only their
fiber. Nothing has to be declared or started first:

```php
<?php
// report.php
use function Cairo\{async, await, all};

$count = static function (string $sql): int {
    $pdo = new PDO(getenv('DB_DSN'), getenv('DB_USER'), getenv('DB_PASSWORD'));
    return (int) $pdo->query($sql)->fetchColumn();
};

$tasks = [
    'orders' => async(fn () => $count('SELECT count(*) FROM orders')),
    'invoices' => async(fn () => $count('SELECT count(*) FROM invoices')),
    'refunds' => async(fn () => $count('SELECT count(*) FROM refunds')),
];
print_r(await(all($tasks)));   // the three queries run at the same time
```

```sh
cairo php report.php
```

The script itself is a fiber, the first one, and each `async()` starts
another on the same thread. `sleep()`, sockets, curl, PDO and the `Cairo\`
clients suspend the fiber that waits and the others go on: 50 tasks that each
sleep one second end after one second, and 20 tasks that each run a
one-second query end after about one second too, each on a connection of its
own.

What to know:

- **A script that starts no task pays nothing.** While the script is the only
  fiber that could run, a wait blocks the thread as it does under `php`, with
  no turn through the scheduler. `artisan`, Composer and a script of your own
  run as they did.
- **Tasks end with the script.** When the script comes to its end, or calls
  `exit()`, the tasks nobody waited for are canceled: their context ends, and
  with it what they wait for. `await()` what has to finish.
- **`offload()` runs the job in place.** A command has one PHP thread; the
  offload pool is the server's.
- **The script's variables are the globals**, its stack is the bottom of the
  backtrace, and it has 16 MiB of stack for deep recursion. A task has
  `fiber.stack_size` (2 MiB unless you set it), as in a request.
- **Shutdown functions and destructors that run after the script** run with
  no scheduler: a wait there blocks, and `async()` runs its task to the end
  before it returns.
- **A wait that nothing can end stops the command.** When every fiber is
  asleep and no timer, socket or operation could wake one (a `recv()` on a
  channel that nobody sends to), Cairo says so on standard error and the
  status is 255, instead of hanging.

### Programs with their own event loop

A library with an event loop of its own for fibers, such as amphp v3 on
Revolt, suspends the script's fiber and expects its own loop to resume it.
Under Cairo's scheduler nothing does, and the command ends with the message
above. Run such a program outside the scheduler:

```sh
CAIRO_SCHEDULER=off cairo php worker.php
```

The script then runs as under `php`, in no fiber: waits block, `async()` runs
its task to the end before it returns, and a `Channel` that has to wait for
another fiber throws a `LogicException`.

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

A worker stops as it does under PHP, because the binary [handles
signals](#signals) for scripts:

- `SIGTERM` is what `docker stop`, Kubernetes, systemd and Supervisor send.
  Laravel's `queue:work` finishes the job in hand and then ends, and
  Symfony's `messenger:consume` does the same.
- A job that runs past the worker's `--timeout` ends the worker, which your
  supervisor starts again.
- `SIGINT` (Ctrl-C) reaches a console command that listens for it.

## Signals

The binary has PHP's own `pcntl` extension for scripts, so code that handles
signals runs unchanged:

```php
pcntl_async_signals(true);
pcntl_signal(SIGTERM, function () use (&$stop): void {
    $stop = true;
});
pcntl_alarm(60);
```

`pcntl_signal()`, `pcntl_async_signals()`, `pcntl_signal_dispatch()`,
`pcntl_signal_get_handler()`, `pcntl_alarm()`, the `SIG*` constants and the
rest of the extension are there, and `extension_loaded('pcntl')` is true,
which is what Laravel, Symfony and Composer ask before they use it.

What differs from `php` is who receives the signal. The system delivers a
signal to any thread of a process, and most threads of the binary are Go's,
where no PHP runs. So Go receives the signal and brings it to the script,
which handles it in one of two ways:

- **A script that runs one fiber at a time**, which is every script that
  does not use `async()`, is interrupted as under PHP. The handler runs at
  the script's next statement. A `sleep()`, `usleep()` or `stream_select()`
  in progress returns early, and an exception that the handler throws
  arrives in the code that was running.
- **A script with several fibers** has its handler run inside a fiber, at
  once: in the fiber that is running, at its next statement, or, while all
  of them wait, in a fiber that Cairo keeps for this. The waits of the
  other fibers are not cut short: a fiber in `sleep(30)` sleeps on.

A handler is for a note, not for work. PHP lets no fiber switch while a
handler runs, so with several fibers a handler that waits (a query,
`sleep()`, `Cairo\sleep()`, `await()`, a `send()` to a full channel) gets a
`FiberError`, "Cannot switch fibers in current execution context". It sets
a flag, or hands the signal to a fiber over a channel with `trySend()`,
which never waits, and the fiber does the work. A script that runs one
fiber at a time is the exception: there a handler waits with the thread
through PHP's own functions, as under PHP, and a Laravel worker's timeout
handler does its queries.

```php
$stop = new Cairo\Channel(1);
pcntl_signal(SIGTERM, static fn () => $stop->trySend(true));

$running = true;
$worker = Cairo\async(function () use (&$running): void {
    while ($running) {
        work();           // its waits suspend only this fiber
    }
});

$stop->recv();            // the script waits here for SIGTERM
$running = false;
Cairo\await($worker);     // the job in hand finishes
```

What to know:

- An exception that a handler throws while every fiber waits has no running
  code to arrive in. It ends the command as an uncaught exception, with
  status 255.
- Left out: `pcntl_fork()`, `pcntl_rfork()` and `pcntl_forkx()`, because a
  fork copies one thread of a process that has many, Go's among them; and
  `pcntl_sigwaitinfo()` and `pcntl_sigtimedwait()`, because no signal
  arrives on its own on a thread that waits for one. Code that asks with
  `function_exists()` first does without them: `artisan tinker` runs, and
  does not fork.
- A script that handles a signal is never [a script that nothing can
  wake](#concurrency-in-a-script): a signal could. A program with an event
  loop of its own for fibers that also handles signals waits for ever
  under the scheduler, with no message. Run it with
  [`CAIRO_SCHEDULER=off`](#programs-with-their-own-event-loop), where its
  signals work as well.
- A signal reaches the script a moment after it reached the process,
  through Go: about a tenth of a millisecond. A script that sends itself a
  signal and calls `pcntl_signal_dispatch()` in the next statement finds
  nothing yet. A signal that arrives while the script's last statement
  runs is not handled, as under PHP.
- A signal that the script has no handler for does what it does to the
  Cairo binary. `SIGINT`, `SIGTERM` and `SIGHUP` end the command, as under
  PHP. `SIGUSR1`, `SIGUSR2` and `SIGALRM` are ignored, where `php` would
  end: a `pcntl_alarm()` with no handler for `SIGALRM` does nothing.
- The server has none of this. In `cairo serve` the `pcntl_*` functions do
  not exist, although `extension_loaded('pcntl')` is true there too: a
  handler in a request would take the signals that stop the server.

`examples/cli/signals.php` in the Cairo repository has a worker that stops
after the job in hand, a job with a time limit, and a script that waits for
a signal on a channel.

## Commands in another PHP

A command may need what an ordinary PHP has and the one in the binary does
not: `pcntl_fork()`, an extension that you compiled for your own PHP, the
interactive shell. Name that PHP in `CAIRO_PHP_CLI`, and Cairo hands every
command to it:

```sh
export CAIRO_PHP_CLI=/usr/bin/php     # a path, or a name on PATH
cairo php artisan horizon             # runs /usr/bin/php artisan horizon
```

This is how servers that keep PHP's command line apart from the server
work, FrankenPHP's image among them. It applies to `cairo php`, to the
[name `php`](#the-name-php) and to the commands that PHP code starts through
`PHP_BINARY`. The process becomes that PHP: the arguments, the signals and
the exit status are its own. The server is not affected: `cairo serve`
always runs the PHP in the binary.

What to know:

- It is another PHP. It has no `Cairo\` classes and no scheduler, it reads
  its own `php.ini`, and it has the extensions that it was built with:
  PostgreSQL needs its `pdo_pgsql`, and a version or an extension that
  differs from the server's shows only in commands.
- Cairo refuses a `CAIRO_PHP_CLI` that names the Cairo binary itself, under
  any name, the `php` link included.
- In an image, start from one that has PHP and add the binary:

  ```dockerfile
  FROM php:8.5-cli
  RUN docker-php-ext-install pcntl pdo_mysql
  COPY --from=ghcr.io/cairophp/cairo:latest /usr/local/bin/cairo /usr/local/bin/cairo
  ENV CAIRO_PHP_CLI=/usr/local/bin/php
  ```

## Starting up

A command starts in about the time of `php` plus the start of the Cairo
binary: on the machine these pages were measured on, `cairo php -r ''` took
35 ms against 20 ms for the PHP 8.5 command line, with the scheduler or
without it. Opcache follows
`opcache.enable_cli`, which is off unless your `php.ini` turns it on.

`examples/cli` in the Cairo repository has a command that reads its
arguments, standard input and a database, and one that runs its queries at
the same time (`together`).

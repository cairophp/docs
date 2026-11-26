# Reloading the code

A PHP thread of Cairo runs `server.php` once and keeps what it has loaded:
that is what makes a request fast, and it is why a file you change is not
what the next request runs. New code needs new threads. Cairo gives a running
server new threads in two ways:

```sh
cairo serve server.php --watch    # development: whenever a file changes
kill -USR1 <pid>                  # a deploy: once, when you say so
```

## What a reload does

- Cairo starts one new PHP thread, which runs `server.php` with the code
  that is on disk now. **When that fails, nothing changes**: a syntax error,
  or an exception while the app boots, is in the log, and the server runs on
  with the code it has.

  ```
  level=ERROR msg="PHP Parse error:  syntax error, unexpected token \"}\" in /app/src/Home.php on line 12" source=php
  level=ERROR msg="php code not reloaded" because=/app/src/Home.php err="cairo: the new code did not start (see the PHP errors above); the server keeps running the code it has"
  ```

- Then each request thread is replaced, as a thread is
  [recycled](supervision.md): its replacement boots, takes over the new
  requests, and the old thread finishes the requests it holds, with the code
  they began with. **No request is refused, and none fails.** A quarter of
  the threads is replaced at a time, so a reload does not double PHP's
  memory.
- The [offload](concurrency.md) threads finish the jobs they hold and start
  anew. Jobs that come meanwhile wait for them.

```
level=INFO msg="php code reloaded" because=/app/src/Home.php took=6ms
```

A request that is in flight for long (a stream, a WebSocket) keeps its old
thread, and its old code, until it ends.

## `--watch`

```sh
cairo serve server.php --watch
cairo serve server.php --watch-path src --watch-path config --watch-path .env
```

`--watch` looks at the directory of the server file and everything under it,
or at the directory above it when that one has the `composer.json` and the
server file's does not: a front controller such as Symfony's `public/index.php`
is served from a directory below the app's code.
`--watch-path` names the directories and files to look at instead, and can be
repeated; the server file itself is always watched.

Under a directory, Cairo watches the files a PHP app is made of: `*.php`,
`*.twig`, `*.yaml`, `*.yml`, `.env`, `.env.*` and `composer.lock`. It leaves
out `vendor` (a change there shows in `composer.lock`), `node_modules`,
`storage` and `var` (where frameworks write while they run), and every
directory whose name begins with a dot. A file that you name with
`--watch-path` is watched whatever it is called, and so is a directory you
name, even one of those.

Cairo finds changes by looking: it reads the times and sizes of the files
every 250 ms, and reloads once they have stood still for 100 ms, so a
checkout or an editor that writes several files is one reload. It does not
use the kernel's file events. Those do not arrive for a directory that is
shared with a container or mounted over a network, which is where a
development server often runs. A scan reads the times of the files,
not the files. Measured here: 0.13 ms for a Laravel app outside `vendor` (33
files), 8 ms for 5,000 files, and 120 ms for 50,000, which at four scans a
second is half a CPU core: for an app that big, name the directories of the
code with `--watch-path`. More than 200,000 files is refused, with a hint to
do that.

`--watch` is for development. It costs nothing per request, but a server in
production should get its code when you decide, with the signal.

## The signal

```sh
kill -USR1 "$(pidof cairo)"
```

SIGUSR1 reloads once. A deploy puts the new code in place and sends it. A
deploy that points a link at a new release directory works too, when the
server was started through the link (`cairo serve /app/current/server.php`):
the new threads follow the link again.

With the [Laravel Octane driver](https://github.com/cairophp/octane),
`php artisan octane:reload --server=cairo` sends this signal, and
`octane:start --server=cairo --watch` starts Cairo with `--watch` on the
directories of `config('octane.watch')`.

## What needs a new process

Some things are made once, when the process starts, and a new thread cannot
change them:

- **What `server.php` declares**: the servers and their addresses, the
  routes, the middleware and the settings of the app. Go built the servers
  from that.
- **The environment.** A library that reads a `.env` file (vlucas/phpdotenv,
  as Laravel uses it) puts the values in the process's environment and
  leaves alone what is set there already. A thread that starts later would
  keep the old values.
- **`php.ini`**, and files loaded with `opcache.preload`.

With `--watch`, Cairo sees the first two and starts the process anew in
place: it stops as on SIGTERM, with the requests in flight finished, and
starts again under the same process id. Until the new process listens,
which takes as long as your app takes to start, connections are refused.

```
level=INFO msg="restarting in place" because=/app/server.php why="server.php declares other servers, routes or settings"
```

The signal never restarts. A reload that finds another declaration is
refused, and the server runs on with the code it has:

```
level=ERROR msg="php code not reloaded" because=signal err="cairo: server.php declares other servers, routes or settings than the running server has: restart it"
```

After a deploy that changes one of these, restart the server instead of
reloading it. Do not leave it at a refused reload for long. A thread that is
[recycled](supervision.md) later reads the new code as well and cannot start
either: the old thread then stays in its place, serves on with the code it
has, and Cairo tries again after 1 s, 2 s, 4 s and so on, a minute at most,
with an error in the log each time:

```
level=ERROR msg="php thread not replaced" thread=0 reason=max_requests err="cairo: server.php declares other servers, routes or settings than the running server has: restart it" again_in=1s
```

A thread that dies has no old thread to fall back on: it can only start with
the code on disk, and after five tries the server stops.

## opcache

You do not have to reset opcache, and should not: `opcache_reset()` makes
Cairo [restart in place](supervision.md#when-opcache-has-to-restart).
Threads that start after the first reload have opcache compare each file it
has with the file on disk, whatever `opcache.validate_timestamps` says in
`php.ini`. Files are read once per thread, so this costs nothing per
request.

This works with `opcache.validate_timestamps=0` too, as production setups
often have it. opcache records no time for a file it compiles with that
setting, so it could not tell an old file from a new one later. Where
`php.ini` turns it off, each PHP thread turns it on with an
`opcache.revalidate_freq` of ten years, once, as it starts: opcache records
the time of each file as it compiles it, which it reads anyway, and never
looks at the disk again until a reload. Without a reload, the cache behaves
as `php.ini` says, and no request pays for it. `ini_get()` shows the two
values the threads run with; `get_cfg_var()` still shows `php.ini`'s.

The new code goes into the cache beside the old, which the old threads still
run, and the old code stays there as stale memory. When the cache is full,
opcache has to empty it, which is only safe in a new process: a reload that
runs into that starts the server anew in place, with the new code, and says
so in the log. Give opcache room (`opcache.memory_consumption`,
`opcache.max_accelerated_files`) for a few generations of the code you
deploy between restarts.

All of this is so with PHP 8.4 or newer, which the released binary and the
image have. A Cairo that you build against PHP 8.1 to 8.3 cannot see opcache's
restart coming, so there the threads that start after the first reload do
not use opcache: each compiles the app for itself, which costs memory and
start time per thread, and nothing per request.

opcache tells versions of a file apart by the second of its time. With
`opcache.file_update_protection=0`, a file that is changed twice within one
second can keep its first version; leave that setting at its default of 2.

## Limits

- A reload gives new code to new requests. It does not change what a
  request in flight runs.
- Under `--watch`, a restart in place closes the connections that are open,
  streams and WebSockets included.
- The scripts of `cairo php` are not servers: neither `--watch` nor the
  signal applies to them.
- The watcher compares the time and the size of each file: a change that
  keeps both is not seen.

`examples/reload` in the Cairo repository is a server to try this on.

# Isolated mode

Apps that are a set of scripts, such as WordPress, need a fresh PHP request
for every request instead: see [Classic mode](classic.md).

Apps that keep request state in globals or singletons (many Laravel and
Symfony apps, most legacy code) can run with one request per PHP thread at a
time:

```php
$app->concurrency('isolated')
    ->resetAfterRequest($container->get(CurrentUser::class), fn () => Cache::flushLocal());

$http->get('/legacy', function (): void {     // classic PHP works
    header('Content-Type: application/json');
    echo json_encode(['id' => $_GET['id'], 'ip' => $_SERVER['REMOTE_ADDR']]);
});
```

In isolated mode Cairo fills `$_GET`, `$_POST` (url-encoded and multipart
forms), `$_FILES`, `$_COOKIE`, `$_SERVER` and `$_REQUEST`; a handler that returns nothing answers with what it
echoed, its `header()` calls and `http_response_code()`. `flush()` sends what
was echoed so far, and `headers_send(103)` and `fastcgi_finish_request()`
work as under other PHP servers: see [Streamed answers](streaming.md). After each request it
clears the superglobals and calls `reset()` on everything given to
`resetAfterRequest()` (any object with a `reset()` method, such as
`Cairo\Resettable` or Symfony's `ResetInterface`, or a callable). Requests that
arrive while every thread is busy wait in Go, in one first-in, first-out
queue, and go to the next thread that is free, so a slow request never holds
up the ones behind it while another thread is idle. Use more threads in this
mode.

Uploads are parsed by Go into temporary files that are removed after the
request. `move_uploaded_file()` and `is_uploaded_file()` accept them in both
modes; in fiber mode use `$req->form()` and `$req->file('photo')`, which gives a
`Cairo\Http\UploadedFile` with `name`, `type`, `size`, `path`, `contents()` and
`moveTo()`.

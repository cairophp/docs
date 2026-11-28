"""Illustrations of concurrency in each way Cairo runs PHP (modes.md and the mode pages)."""
from ill import Lane, Mark, Scene, Step, Tok

FIBERS = Scene(
    id="mode-fibers",
    title="Fiber mode: many requests on one thread",
    code=[("server.php", "php", """$app = new Cairo\\App();
$app->threads(1);                // one PHP thread

$http = $app->http(':8080');
$http->get('/order/{id}', function (Request $r) {
    $q = db()->prepare(ORDER_SQL);
    $q->execute([$r->param('id')]);  // 50 ms
    return Response::json($q->fetch());
});
return $app;
""")],
    lanes=[Lane("go", "Go · net/http", "go", "accepts every connection"),
           Lane("t1", "PHP thread 1", "php", "a fiber per request"),
           Lane("wait", "Parked on thread 1", "wait", "its own epoll, no goroutine")],
    tokens=[Tok("A", "req A", 0), Tok("B", "req B", 1), Tok("C", "req C", 2)],
    marks=[Mark("sleep", "thread sleeps: nothing to run", "t1", 2, "muted")],
    steps=[
        Step("Three requests arrive at once. Go accepts them and hands all three to thread 1: in fiber mode one thread takes many requests.",
             lines=["get('/order"], clock="0 ms", at={"A": ("go", 0), "B": ("go", 1), "C": ("go", 2)}),
        Step("A starts in a fiber of its own and sends its query to MySQL.",
             lines=["prepare(", "execute("], at={"A": ("t1", 0)}, lit=("t1",)),
        Step("The query waits on a socket, so only A's fiber suspends. The thread watches that socket in its own epoll and starts B about a microsecond later.",
             lines=["execute("], clock="0.001 ms", at={"A": ("wait", 0), "B": ("t1", 1)}, lit=("t1",)),
        Step("B parks on its query too, and C starts. Each request uses the thread for microseconds; the waiting costs it nothing.",
             lines=["execute("], at={"B": ("wait", 1), "C": ("t1", 2)}, lit=("t1",)),
        Step("All three wait at the same time. With nothing to run, the thread sleeps until a socket is ready or Go has work for it.",
             at={"C": ("wait", 2)}, show=("sleep",)),
        Step("A's rows arrive after 50 ms. The epoll wakes A's fiber, which builds its answer.",
             lines=["return Response::json"], clock="50 ms", at={"A": ("t1", 0)}, lit=("t1",)),
        Step("A's answer goes back to Go, and B and C wake the same way.",
             lines=["return Response::json"], at={"A": ("go", 0, "done"), "B": ("t1", 1), "C": ("t1", 2)}, lit=("t1",)),
        Step("Three requests took one wait, not three. With one thread, 50 requests that each wait 1 s finish in about 1 s.",
             clock="≈ 50 ms", at={"B": ("go", 1, "done"), "C": ("go", 2, "done")}),
    ],
)

ISOLATED = Scene(
    id="mode-isolated",
    title="Isolated mode: one request per thread, parallel tasks inside it",
    code=[("server.php", "php", """$app = new Cairo\\App();
$app->concurrency('isolated')->threads(2);

$http = $app->http(':8080');
$http->get('/home', function () {
    $id = (int) $_GET['user'];
    [$user, $feed] = await(all([
        async(fn () => loadUser($id)),
        async(fn () => loadFeed($id)),
    ]));
    echo json_encode([$user, $feed]);
});
return $app;
""")],
    lanes=[Lane("go", "Go · one FIFO queue", "go", "requests wait here, not on a thread"),
           Lane("t1", "PHP thread 1", "php", "one request at a time"),
           Lane("t2", "PHP thread 2", "php", "one request at a time")],
    tokens=[Tok("A", "req A", 0), Tok("B", "req B", 1), Tok("C", "req C", 2),
            Tok("a1", "user", 0, True), Tok("a2", "feed", 0, True)],
    marks=[Mark("reset", "superglobals cleared, resets run", "t1", 2.4, "nile"),
           Mark("q", "waits for a free thread", "go", 2.6, "muted")],
    steps=[
        Step("Three requests arrive and there are two threads. In isolated mode a thread runs one request at a time.",
             lines=["concurrency('isolated')"], clock="0 ms", at={"A": ("go", 0), "B": ("go", 1), "C": ("go", 2)}),
        Step("A starts on thread 1 and B on thread 2. C waits in Go's first-in, first-out queue, so a slow request never holds it while another thread is free.",
             lines=["get('/home'", "$_GET"], at={"A": ("t1", 0), "B": ("t2", 0), "C": ("go", 0)}, show=("q",), lit=("t1", "t2")),
        Step("Inside A, `async()` starts two fibers on thread 1, and A's own fiber waits for both.",
             lines=["async(fn () => loadUser", "async(fn () => loadFeed"], at={"A": ("t1", 0, "wait"), "a1": ("t1", 1.1), "a2": ("t1", 1.9)}, show=("q",)),
        Step("Both queries wait at the same time, on thread 1's epoll. The request takes one wait instead of two.",
             lines=["await(all("], clock="0.01 ms", at={"a1": ("t1", 1.1, "wait"), "a2": ("t1", 1.9, "wait")}, show=("q",)),
        Step("Both results are in. A's fiber resumes and echoes its answer: `$_GET`, `echo` and `header()` work as in classic PHP.",
             lines=["echo json_encode"], clock="40 ms", at={"a1": ("-",), "a2": ("-",), "A": ("t1", 0)}, show=("q",), lit=("t1",)),
        Step("A is answered. Cairo clears the superglobals and calls what `resetAfterRequest()` names, so the next request starts clean.",
             at={"A": ("go", 1, "done")}, show=("reset", "q")),
        Step("C goes to thread 1, the first thread that is free. Requests run in parallel across threads, and tasks in parallel within a request.",
             clock="41 ms", at={"C": ("t1", 0), "B": ("go", 2, "done")}, lit=("t1",)),
    ],
)

CLASSIC = Scene(
    id="mode-classic",
    title="Classic mode: a fresh PHP request for every request",
    code=[("server.php", "php", """$app = (new Cairo\\App())
    ->concurrency('classic')
    ->threads(2);
$app->http(':8080')->scripts(__DIR__ . '/public');
return $app;
"""), ("public/report.php", "php", """<?php
use function Cairo\\{async, await, all};

$orders = async(fn () => count_rows('orders'));
$refunds = async(fn () => count_rows('refunds'));
echo json_encode(await(all([$orders, $refunds])));
""")],
    lanes=[Lane("go", "Go · scripts() router", "go", "path to script, FIFO queue"),
           Lane("t1", "PHP thread 1", "php", "runs on its own stack"),
           Lane("t2", "PHP thread 2", "php", "runs on its own stack")],
    tokens=[Tok("A", "report", 0), Tok("B", "index", 1), Tok("C", "login", 2),
            Tok("a1", "orders", 0, True), Tok("a2", "refunds", 0, True)],
    marks=[Mark("new1", "new PHP request", "t1", 2.3, "nile"), Mark("new2", "new PHP request", "t2", 2.3, "nile"),
           Mark("free", "request ends, memory freed", "t1", 2.4, "nile")],
    steps=[
        Step("Requests arrive. Go matches each path to a script under `public/`, as nginx's `try_files` does for PHP-FPM.",
             lines=["scripts(__DIR__"], clock="0 ms", at={"A": ("go", 0), "B": ("go", 1), "C": ("go", 2)}),
        Step("Each thread starts a new PHP request for its script, as a PHP-FPM worker does: the script loads its files, and its globals are its own.",
             lines=["concurrency('classic')", "<?php"], at={"A": ("t1", 0), "B": ("t2", 0), "C": ("go", 0)}, show=("new1", "new2"), lit=("t1", "t2")),
        Step("The script runs on the thread's own stack, not in a fiber. `async()` starts two fibers of this request, and their queries go out at once.",
             lines=["$orders = async", "$refunds = async"], at={"a1": ("t1", 1.1), "a2": ("t1", 1.9)}),
        Step("`await()` lets the two fibers wait together on the thread's epoll. A query outside `async()` would hold the thread, as it holds a PHP-FPM worker.",
             lines=["await(all("], at={"A": ("t1", 0, "wait"), "a1": ("t1", 1.1, "wait"), "a2": ("t1", 1.9, "wait")}),
        Step("Both counts arrive after one wait, and the script echoes its answer.",
             lines=["echo json_encode"], clock="30 ms", at={"a1": ("-",), "a2": ("-",), "A": ("t1", 0)}, lit=("t1",)),
        Step("The PHP request ends and frees all it made. The next request on thread 1 starts from nothing again.",
             clock="31 ms", at={"A": ("go", 3, "done"), "C": ("t1", 0)}, show=("free",)),
    ],
)

PLAIN = Scene(
    id="mode-plain",
    title="No declaration: a folder served as PHP-FPM serves it",
    code=[("terminal", "sh", "cairo serve public/ --threads 2\n"),
          ("public/index.php", "php", """<?php
use function Cairo\\{async, await, all};

$prices = async(fn () => fetch_prices());
$stock = async(fn () => fetch_stock());
[$p, $s] = await(all([$prices, $stock]));
render('home', ['prices' => $p, 'stock' => $s]);
""")],
    lanes=[Lane("go", "Go · no server.php", "go", "a deadline, no middleware"),
           Lane("t1", "PHP thread 1", "php", "PHP's own SAPI request"),
           Lane("t2", "PHP thread 2", "php", "PHP's own SAPI request")],
    tokens=[Tok("A", "GET /", 0), Tok("B", "POST /", 1),
            Tok("a1", "prices", 0, True), Tok("a2", "stock", 0, True)],
    marks=[Mark("none", "no Cairo\\App: serve the folder", "go", 2.7, "muted"),
           Mark("sapi", "PHP parses cookies and forms", "t2", 2.3, "nile"),
           Mark("ready", "async() is there already", "t1", 3.3, "nile"),
           Mark("end", "request ends", "t1", 2.4, "nile")],
    steps=[
        Step("`cairo serve` finds no `Cairo\\App` in `public/`, so it serves the folder the way nginx and PHP-FPM do. There is nothing to declare.",
             lines=["cairo serve"], clock="0 ms", at={"A": ("go", 0), "B": ("go", 1)}, show=("none",)),
        Step("Each request is PHP's own SAPI request. PHP itself fills `$_GET`, `$_POST`, `$_COOKIE` and `$_FILES`, and runs `index.php` with no Cairo PHP code around it.",
             lines=["<?php"], at={"A": ("t1", 0), "B": ("t2", 0)}, show=("sapi",), lit=("t1", "t2")),
        Step("Cairo's concurrency functions are there before the script runs. `async()` starts a fiber for each call.",
             lines=["$prices = async", "$stock = async"], at={"a1": ("t1", 1.1), "a2": ("t1", 1.9)}, show=("ready",)),
        Step("`await()` lets both calls wait at the same time. The rest of Cairo's runtime loads only if the script uses it.",
             lines=["await(all("], at={"A": ("t1", 0, "wait"), "a1": ("t1", 1.1, "wait"), "a2": ("t1", 1.9, "wait")}),
        Step("Both answers are in after one wait, and the page renders.",
             lines=["render("], clock="80 ms", at={"a1": ("-",), "a2": ("-",), "A": ("t1", 0)}, lit=("t1",)),
        Step("The answer goes out through Go and the PHP request ends. Every request behaves the same: nothing carries over to the next.",
             clock="81 ms", at={"A": ("go", 3, "done"), "B": ("go", 4, "done")}, show=("end",)),
    ],
)

CLI = Scene(
    id="mode-cli",
    title="cairo php: a script under the scheduler",
    code=[("terminal", "sh", "cairo php report.php\n"),
          ("report.php", "php", """<?php
use function Cairo\\{async, await, all};

$tasks = [
    async(fn () => count_rows('orders')),
    async(fn () => count_rows('invoices')),
    async(fn () => count_rows('refunds')),
];
print_r(await(all($tasks)));   // ≈ 1 s, not 3
""")],
    lanes=[Lane("t0", "PHP thread 0", "php", "the script is its one request"),
           Lane("wait", "Parked on thread 0", "wait", "timers and sockets"),
           Lane("out", "Terminal", "queue", "no server starts")],
    tokens=[Tok("S", "script", 0), Tok("o", "orders", 1, True), Tok("i", "invoices", 2, True), Tok("r", "refunds", 3, True)],
    marks=[Mark("alone", "alone: waits use the thread", "t0", 2.6, "muted"),
           Mark("exit", "exit status 0", "out", 1.6, "nile")],
    steps=[
        Step("`cairo php` starts one PHP thread and no server. The script runs as the first fiber of Cairo's scheduler.",
             lines=["cairo php"], clock="0 s", at={"S": ("t0", 0)}, show=("alone",)),
        Step("While the script is the only fiber, a wait blocks the thread as under `php`: a script that starts no task pays nothing.",
             lines=["<?php"], at={"S": ("t0", 0)}, show=("alone",), lit=("t0",)),
        Step("Each `async()` starts another fiber on the same thread.",
             lines=["count_rows('orders')", "count_rows('invoices')", "count_rows('refunds')"], at={"o": ("t0", 1.2), "i": ("t0", 2), "r": ("t0", 2.8)}),
        Step("`await()` parks the script's fiber, and the three queries wait on the thread's epoll at the same time.",
             lines=["print_r("], at={"S": ("t0", 0, "wait"), "o": ("wait", 0.4), "i": ("wait", 1.2), "r": ("wait", 2)}),
        Step("The three counts arrive together: three one-second queries take about one second.",
             lines=["print_r("], clock="1 s", at={"o": ("t0", 1.2, "done"), "i": ("t0", 2, "done"), "r": ("t0", 2.8, "done"), "S": ("t0", 0)}, lit=("t0",)),
        Step("The script prints and ends, and so does the command. A task nobody awaited would be canceled here.",
             at={"o": ("-",), "i": ("-",), "r": ("-",), "S": ("out", 0, "done")}, show=("exit",)),
    ],
)

SCENES = [FIBERS, ISOLATED, CLASSIC, PLAIN, CLI]

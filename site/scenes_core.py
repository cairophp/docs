"""Illustrations of Cairo's core: a request's way, waits, contexts, offload, reload, request-local statics."""
from ill import Lane, Mark, Scene, Step, Tok

JOURNEY = Scene(
    id="journey",
    title="From server.php to an answer",
    code=[("server.php", "php", """<?php
use Cairo\\App;
use Cairo\\Http\\{Request, Response};

$app = new App();
$app->threads(2);

$http = $app->http(':8080');
$http->get('/hello/{name}', fn (Request $r) =>
    Response::text("Hello {$r->param('name')}"));

return $app;
""")],
    lanes=[Lane("decl", "Declare phase", "queue", "server.php runs once"),
           Lane("go", "Go · net/http", "go", "listeners, router"),
           Lane("t1", "PHP thread 1", "php", "handlers built"),
           Lane("t2", "PHP thread 2", "php", "handlers built")],
    tokens=[Tok("D", "spec", 6), Tok("R", "/hello", 0)],
    marks=[Mark("rec", "records servers and routes", "decl", 2.4, "muted"),
           Mark("listen", "listening on :8080", "go", 2.6, "nile"),
           Mark("boot1", "runs server.php again", "t1", 2.4, "nile"),
           Mark("boot2", "runs server.php again", "t2", 2.4, "nile"),
           Mark("pick", "the thread that takes it first", "go", 2.6, "muted"),
           Mark("next", "on to its next fiber", "t1", 2.6, "muted")],
    steps=[
        Step("`cairo serve server.php` runs the file once. `App`, `http()` and `get()` only record a description of the servers.",
             lines=["$app = new App()", "$http = $app->http", "$http->get("], at={"D": ("decl", 0)}, show=("rec",), lit=("decl",)),
        Step("The description goes to Go, which opens the listeners and builds the router.",
             lines=["return $app"], at={"D": ("go", 0, "done")}, show=("listen",), lit=("go",)),
        Step("Go starts the PHP threads. Each runs `server.php` again to build its own handlers, then waits for work.",
             lines=["threads(2)"], at={"D": ("-",)}, show=("boot1", "boot2"), lit=("t1", "t2")),
        Step("A request arrives. Go sends it to a thread that is running PHP and will take it within microseconds, or else to the least busy.",
             clock="0 µs", at={"R": ("go", 0)}, show=("pick",)),
        Step("It lands in thread 1's inbox and starts in a new fiber, which runs the handler.",
             lines=["$http->get(", "Response::text"], at={"R": ("t1", 0)}, lit=("t1",)),
        Step("The answer is queued for Go without a call into Go. Go writes it to the client, and the thread goes on with its next fiber.",
             clock="≈ 20 µs", at={"R": ("go", 0, "done")}, show=("next",)),
    ],
)

WAITS = Scene(
    id="waits",
    title="Three waits: a timer, a socket, a Go operation",
    code=[("server.php", "php", """$http->get('/mix', function () use ($greeter, $req) {
    sleep(1);                        // a timer
    $pdo = new PDO(DSN, USER, PASS);
    $pdo->query('SELECT 1');         // a socket
    $reply = $greeter->SayHello($req);   // in Go
    return Response::text($reply->message);
});
""")],
    lanes=[Lane("t1", "PHP thread 1", "php", "runs fibers"),
           Lane("park", "Parked on thread 1", "wait", "timers, epoll, inbox"),
           Lane("go", "Go operation", "go", "a goroutine for the call")],
    tokens=[Tok("F", "req A", 0), Tok("G", "gRPC", 1)],
    marks=[Mark("timer", "a timer the thread keeps", "park", 2.5, "gold"),
           Mark("sock", "socket in the thread's epoll", "park", 2.6, "gold"),
           Mark("ctx", "under the request's deadline", "go", 2.6, "nile"),
           Mark("ev", "result: an event in the inbox", "t1", 2.6, "nile")],
    steps=[
        Step("The request runs in its fiber on thread 1.",
             lines=["get('/mix'"], clock="0 s", at={"F": ("t1", 0)}, lit=("t1",)),
        Step("`sleep()` parks the fiber with a timer that the thread keeps. No goroutine and no system thread are involved: the switch costs about a microsecond.",
             lines=["sleep(1)"], at={"F": ("park", 0)}, show=("timer",)),
        Step("The timer fires after one second and the fiber runs on.",
             lines=["new PDO"], clock="1 s", at={"F": ("t1", 0)}, lit=("t1",)),
        Step("PDO MySQL waits on a socket. The thread watches that socket in its own epoll and wakes the fiber when the rows are there.",
             lines=["query("], at={"F": ("park", 0)}, show=("sock",)),
        Step("A gRPC call is work that Cairo does in Go. It gets a goroutine for the length of the call, and the request's context, so its deadline reaches the call.",
             lines=["SayHello"], clock="1.001 s", at={"F": ("park", 0), "G": ("go", 0, "run")}, show=("ctx",)),
        Step("The reply comes back as an event in the thread's inbox and wakes the fiber. The thread itself never blocked.",
             lines=["return Response::text"], clock="1.004 s", at={"G": ("-",), "F": ("t1", 0)}, show=("ev",), lit=("t1",)),
        Step("The answer is sent. Meanwhile the thread could have run any number of other requests.",
             at={"F": ("t1", 0, "done")}),
    ],
)

CONTEXT = Scene(
    id="context",
    title="A shorter deadline for part of a request",
    code=[("server.php", "php", """$http->get('/page', function ($r, Context $ctx) {
    $short = $ctx->withTimeout(0.3);
    [$profile, $ads] = $short->run(fn () => [
        async(fn () => fetch('/profile')),  // 0.1 s
        async(fn () => fetch('/ads')),      // 2 s
    ]);
    $p = await($profile);
    try {
        $a = await($ads);
    } catch (Context\\DeadlineExceeded) {
        $a = [];
    }
    return Response::json([$p, $a]);
});
""")],
    lanes=[Lane("ctx", "Contexts", "queue", "each ends at its deadline"),
           Lane("t1", "PHP thread 1", "php"),
           Lane("park", "Parked on thread 1", "wait", "curl's sockets")],
    tokens=[Tok("R", "page", 0), Tok("P", "profile", 1, True), Tok("A", "ads", 3, True)],
    marks=[Mark("req", "request: 30 s", "ctx", 0.6, "nile"),
           Mark("child", "child: 0.3 s", "ctx", 2.1, "gold"),
           Mark("ended", "child ended at 0.3 s", "ctx", 2.4, "red"),
           Mark("throw", "DeadlineExceeded", "park", 3.2, "red")],
    steps=[
        Step("Every request has a context, which carries its deadline.",
             lines=["get('/page'"], clock="0 s", at={"R": ("t1", 0)}, show=("req",)),
        Step("`withTimeout(0.3)` makes a child context. The `async()` tasks started inside `run()` inherit it.",
             lines=["withTimeout(0.3)", "fetch('/profile')", "fetch('/ads')"], at={"P": ("t1", 1.1), "A": ("t1", 1.9)}, show=("req", "child")),
        Step("Both calls wait on their sockets, and the request waits for the profile.",
             lines=["$p = await"], at={"R": ("t1", 0, "wait"), "P": ("park", 0.6), "A": ("park", 1.5)}, show=("req", "child")),
        Step("The profile arrives after 0.1 s. The request goes on, and waits for the ads.",
             lines=["$a = await"], clock="0.1 s", at={"P": ("t1", 1.1, "done")}, show=("req", "child")),
        Step("At 0.3 s the child context ends. The ads call is still waiting, so its wait ends too and throws `Context\\DeadlineExceeded` in its own fiber.",
             lines=["catch (Context"], clock="0.3 s", at={"A": ("park", 1.5, "fail")}, show=("req", "ended", "throw")),
        Step("The request catches it and answers without ads. Its own context was never touched.",
             lines=["$a = [];", "return Response::json"], at={"A": ("-",), "P": ("-",), "R": ("t1", 0)}, show=("req", "ended")),
        Step("Answered at 0.3 s instead of 2 s.",
             at={"R": ("t1", 0, "done")}, show=("req",)),
    ],
)

OFFLOAD = Scene(
    id="offload",
    title="CPU work on the offload threads",
    code=[("server.php", "php", """$app->threads(1)->offloadThreads(2);

$http = $app->http(':8080');
$http->post('/signup', function (Request $r) {
    $form = $r->form();
    $hash = offload('password_hash',
        $form['password'], PASSWORD_ARGON2ID);
    saveUser($form['email'], $hash);
    return Response::json(['ok' => true], 201);
});
$http->get('/ping', fn () => Response::text('pong'));
""")],
    lanes=[Lane("go", "Go · net/http", "go"),
           Lane("t1", "PHP thread 1", "php", "request thread"),
           Lane("off", "Offload threads", "off", "CPU work")],
    tokens=[Tok("S", "signup", 0), Tok("P", "ping", 1), Tok("J", "hash job", 3)],
    marks=[Mark("free", "thread 1 stays free", "t1", 2.8, "nile")],
    steps=[
        Step("A sign-up arrives and runs on thread 1.",
             lines=["post('/signup'", "$form = "], clock="0 ms", at={"S": ("t1", 0)}, lit=("t1",)),
        Step("`offload()` serializes the job and queues it straight into the inbox of the offload thread with the least to do. Only the request's fiber waits.",
             lines=["offload('password_hash'", "PASSWORD_ARGON2ID"], at={"S": ("t1", 0, "wait"), "J": ("off", 0)}, show=("free",)),
        Step("A `/ping` comes in while the hash computes on another thread, so thread 1 runs it at once.",
             lines=["get('/ping'"], clock="5 ms", at={"P": ("t1", 1)}, show=("free",), lit=("t1",)),
        Step("`/ping` is answered without waiting for the hash.",
             at={"P": ("go", 1, "done")}, show=("free",)),
        Step("The result goes straight back to thread 1's inbox and wakes the fiber.",
             lines=["saveUser("], clock="50 ms", at={"J": ("-",), "S": ("t1", 0)}, lit=("t1",)),
        Step("The sign-up is answered. An empty job costs about 35 µs, so `offload()` is for work that takes longer than that.",
             lines=["return Response::json"], at={"S": ("go", 0, "done")}),
    ],
)

RELOAD = Scene(
    id="reload",
    title="New code without dropping a request",
    code=[("terminal", "sh", """# development: whenever a file changes
cairo serve server.php --watch

# a deploy: once, when you say so
kill -USR1 "$(pidof cairo)"
""")],
    lanes=[Lane("boot", "Starting", "queue", "runs server.php from disk"),
           Lane("pool", "Request threads", "php", "take new requests"),
           Lane("old", "Finishing", "wait", "old code, requests in flight")],
    tokens=[Tok("o1", "old 1", 6), Tok("o2", "old 2", 6), Tok("n1", "new 1", 0), Tok("n2", "new 2", 0),
            Tok("r", "req", 1, True)],
    marks=[Mark("change", "src/Home.php changed", "boot", 2.5, "gold"),
           Mark("fail", "fails to boot? nothing changes", "boot", 2.5, "muted"),
           Mark("done", "php code reloaded", "pool", 3.1, "nile")],
    steps=[
        Step("Two request threads serve with the code they loaded when they started.",
             lines=["--watch"], at={"o1": ("pool", 0), "o2": ("pool", 1)}),
        Step("A file changes, or the process gets `SIGUSR1`. Cairo starts one new thread as a trial, which runs `server.php` with the code on disk now.",
             lines=["--watch", "kill -USR1"], at={"n1": ("boot", 0)}, show=("change",), lit=("boot",)),
        Step("A parse error or an exception at boot would end here: nothing is replaced, and the server runs on with the code it has.",
             at={"n1": ("boot", 0)}, show=("fail",), lit=("boot",)),
        Step("It booted, so it takes thread 1's place and the new requests. The old thread finishes the request it holds, with the code it began with.",
             at={"n1": ("pool", 0), "o1": ("old", 0), "r": ("old", 0.85, "run")}),
        Step("Then the next thread. A quarter of the threads is replaced at a time, so a reload never doubles PHP's memory.",
             at={"r": ("-",), "o1": ("-",), "n2": ("boot", 0)}, lit=("boot",)),
        Step("No request was refused and none failed. The offload threads finish their jobs and start anew too.",
             at={"n2": ("pool", 1), "o2": ("-",)}, show=("done",)),
    ],
)

REQUEST_LOCAL = Scene(
    id="request-local",
    title="A static that each request keeps for itself",
    code=[("server.php", "php", """use Cairo\\RequestLocal;

RequestLocal::register(Tenant::class, 'current');

$http->get('/orders', function (Request $r) {
    Tenant::$current = $r->header('X-Tenant');
    $rows = loadOrders();            // waits
    return Response::json([Tenant::$current, $rows]);
});
""")],
    lanes=[Lane("val", "Tenant::$current", "queue", "what each request sees"),
           Lane("t1", "PHP thread 1", "php"),
           Lane("park", "Parked on thread 1", "wait")],
    tokens=[Tok("A", "req A", 0), Tok("B", "req B", 1)],
    marks=[Mark("a", "alice", "val", 0.5, "gold"), Mark("b", "bob", "val", 0.5, "red"),
           Mark("bad", "A reads bob: wrong tenant", "t1", 2.7, "red"),
           Mark("without", "without register()", "val", 2.9, "muted"),
           Mark("with", "with register()", "val", 3.2, "nile"),
           Mark("ra", "A: alice", "val", 0.6, "gold"), Mark("rb", "B: bob", "val", 1.7, "nile"),
           Mark("good", "A reads alice", "t1", 2.7, "nile")],
    steps=[
        Step("Without `register()`, a static belongs to its class, so every request on the thread shares it. A sets its tenant, alice.",
             lines=["Tenant::$current = "], at={"A": ("t1", 0)}, show=("a", "without")),
        Step("A waits on its query, and B runs on the same thread. B sets its tenant, bob.",
             lines=["loadOrders()", "Tenant::$current = "], at={"A": ("park", 0), "B": ("t1", 1)}, show=("b", "without")),
        Step("B waits in turn. A resumes and reads bob: another request's value.",
             lines=["return Response::json"], at={"B": ("park", 1), "A": ("t1", 0)}, show=("b", "bad", "without")),
        Step("With `RequestLocal::register()` in server.php, each request has a slot of its own. A sets alice again.",
             lines=["RequestLocal::register"], at={"A": ("t1", 0), "B": ("-",)}, show=("ra", "with")),
        Step("A waits, and B sets bob in its own slot.",
             lines=["loadOrders()", "Tenant::$current = "], at={"A": ("park", 0), "B": ("t1", 1)}, show=("ra", "rb", "with")),
        Step("A resumes and reads alice. When fibers of two requests take turns, Cairo moves each registered value out and the next one in, which costs about 15 ns.",
             lines=["return Response::json"], at={"B": ("park", 1), "A": ("t1", 0)}, show=("ra", "rb", "good", "with")),
    ],
)

SCENES = [JOURNEY, WAITS, CONTEXT, OFFLOAD, RELOAD, REQUEST_LOCAL]

"""Illustrations of the extensions: runtime hooks, the response cache, gRPC streams, WebSockets and topics, the blocking detector."""
from ill import Lane, Mark, Scene, Step, Tok

HOOKS = Scene(
    id="hooks",
    title="Runtime hooks: PHP's own waits suspend only the fiber",
    code=[("server.php", "php", """$app->threads(1)->hooks(Hook::ALL);  // the default

$http->get('/q', function () {
    $pdo = new PDO(DSN, USER, PASS);
    $pdo->query('SELECT SLEEP(1)');      // mysqlnd
    return Response::text('done');
});
""")],
    lanes=[Lane("go", "Go · net/http", "go"),
           Lane("t1", "PHP thread 1", "php"),
           Lane("park", "Parked on thread 1", "wait", "the thread's epoll")],
    tokens=[Tok("A", "req A", 0), Tok("B", "req B", 1), Tok("C", "req C", 2)],
    marks=[Mark("none", "Hook::NONE", "go", 3.6, "red"), Mark("all", "Hook::ALL", "go", 3.6, "nile"),
           Mark("held", "the thread waits with A", "t1", 2.4, "red"),
           Mark("free", "the thread runs on", "t1", 3.2, "nile")],
    steps=[
        Step("First with `Hook::NONE`. Three requests arrive, and A starts its query.",
             lines=["hooks(Hook::ALL)", "query("], clock="0 s", at={"A": ("t1", 0), "B": ("go", 1), "C": ("go", 2)}, show=("none",)),
        Step("mysqlnd waits for the server with the thread, so B and C cannot start: 20 such requests take 20 seconds.",
             lines=["query("], at={"A": ("t1", 0, "wait")}, show=("none", "held")),
        Step("A is answered after one second, and only then does B start.",
             clock="1 s", at={"A": ("go", 0, "done"), "B": ("t1", 0, "wait")}, show=("none", "held")),
        Step("Now with the hooks on, the default. The same three requests arrive.",
             clock="0 s", at={"A": ("go", 0), "B": ("go", 1), "C": ("go", 2)}, show=("all",)),
        Step("Each query's socket wait becomes a wait of its fiber, parked on the thread's epoll, and the next request starts at once.",
             lines=["query("], at={"A": ("park", 0), "B": ("park", 1), "C": ("park", 2)}, show=("all", "free")),
        Step("All three are answered after one second. With one thread, 50 such requests take about one second. The same goes for `sleep()`, curl, streams and PDO PostgreSQL.",
             lines=["return Response::text"], clock="1 s", at={"A": ("go", 0, "done"), "B": ("go", 1, "done"), "C": ("go", 2, "done")}, show=("all",)),
    ],
)

CACHE = Scene(
    id="response-cache",
    title="The response cache: Go answers without running PHP",
    code=[("server.php", "php", """$http->get('/products', function () use ($db) {
    return Response::json(listProducts($db));
})->cache(ttl: 5, staleWhileRevalidate: 30);
""")],
    lanes=[Lane("go", "Go · router", "go", "looks in the cache first"),
           Lane("cache", "Response cache", "queue", "memory, 64 MiB a server"),
           Lane("t1", "PHP thread 1", "php")],
    tokens=[Tok("A", "req A", 0), Tok("B", "req B", 1), Tok("C", "req C", 2), Tok("D", "req D", 3), Tok("E", "req E", 4),
            Tok("R", "200 OK", 6), Tok("bg", "rebuild", 6, True)],
    marks=[Mark("one", "same key: one build", "go", 3.4, "muted"),
           Mark("nophp", "PHP does not run", "t1", 2.4, "nile"),
           Mark("stale", "stale: served at once", "cache", 2.4, "gold"),
           Mark("fresh", "fresh again", "cache", 2, "nile")],
    steps=[
        Step("Three clients ask for `/products` at once, and nothing is cached yet.",
             lines=["get('/products'"], clock="0 s", at={"A": ("go", 0), "B": ("go", 1), "C": ("go", 2)}),
        Step("A runs the handler. B and C wait for that one build: 256 clients asking at once make one PHP call.",
             lines=["listProducts"], at={"A": ("t1", 0), "B": ("go", 1, "wait"), "C": ("go", 2, "wait")}, show=("one",)),
        Step("The 200 is stored, and all three get it. Only GETs, and only answers without cookies or private caching, are stored.",
             lines=["cache(ttl: 5"], at={"A": ("go", 0, "done"), "B": ("go", 1, "done"), "C": ("go", 2, "done"), "R": ("cache", 0, "done")}),
        Step("Within the 5 s TTL Go answers from memory: the request never reaches PHP. Go middleware still runs.",
             clock="2 s", at={"A": ("-",), "B": ("-",), "C": ("-",), "D": ("go", 0, "done")}, show=("nophp",)),
        Step("After 5 s the copy is stale. For 30 s more Go still answers with it at once, and rebuilds it with one request in the background.",
             lines=["staleWhileRevalidate: 30"], clock="6 s", at={"D": ("-",), "E": ("go", 1, "done"), "R": ("cache", 0, "wait"), "bg": ("t1", 0.2)}, show=("stale",)),
        Step("The new answer replaces the old one. No client waited for the rebuild.",
             clock="6.02 s", at={"bg": ("-",), "R": ("cache", 0, "done")}, show=("fresh",)),
    ],
)

GRPC_STREAM = Scene(
    id="grpc-stream",
    title="A gRPC stream: read ahead, sent from a queue",
    code=[("Greeter.php", "php", """public function Chat(
    ServerStream $stream,
    Context $ctx,
): void {
    foreach ($stream as $request) {  // HelloRequest
        $stream->send(new HelloReply(
            message: "Hi {$request->name}"));
    }
}
""")],
    lanes=[Lane("cli", "Client · HTTP/2", "go"),
           Lane("ra", "Go · read ahead", "queue", "64 messages or 1 MiB"),
           Lane("t1", "PHP thread 1", "php", "the method's fiber"),
           Lane("sq", "Go · send queue", "queue", "64 replies, one writer")],
    tokens=[Tok("H", "Chat()", 0), Tok("m1", "Ada", 1, True), Tok("m2", "Bo", 1, True), Tok("m3", "Cy", 1, True),
            Tok("r1", "Hi Ada", 4, True), Tok("r2", "Hi Bo", 4, True), Tok("r3", "Hi Cy", 4, True)],
    marks=[Mark("noswitch", "no fiber switch", "sq", 2.8, "nile")],
    steps=[
        Step("The client opens the stream. The handler's `foreach` asks for a message, and none has come, so its fiber waits.",
             lines=["foreach ($stream"], at={"H": ("t1", 0, "wait"), "m1": ("cli", 0.4), "m2": ("cli", 1.1), "m3": ("cli", 1.8)}),
        Step("The client sends three messages. Go reads them ahead of the handler.",
             at={"m1": ("ra", 0.4), "m2": ("ra", 1.1), "m3": ("ra", 1.8)}),
        Step("The handler takes all that has arrived. `recv()` waits only when nothing has, so a burst of messages does not cost a wait each.",
             lines=["foreach ($stream"], at={"H": ("t1", 0), "m1": ("t1", 1.3), "m2": ("t1", 2), "m3": ("t1", 2.7)}),
        Step("`send()` puts the reply in Go's queue with one call and returns, without a fiber switch.",
             lines=["$stream->send("], at={"m1": ("-",), "r1": ("sq", 0.4)}, show=("noswitch",)),
        Step("The other two follow, and one goroutine writes the queue to the client. Once 64 replies wait, `send()` waits for room: a slow client holds back only this handler.",
             lines=["$stream->send(", "message:"], at={"m2": ("-",), "m3": ("-",), "r1": ("cli", 0.4, "done"), "r2": ("sq", 1.1), "r3": ("sq", 1.8)}),
        Step("All three replies are out, and the handler waits for the next message like any other wait.",
             lines=["foreach ($stream"], at={"r2": ("cli", 1.1, "done"), "r3": ("cli", 1.8, "done"), "H": ("t1", 0, "wait")}),
    ],
)

TOPICS = Scene(
    id="topics",
    title="WebSockets and a topic",
    code=[("server.php", "php", """$http->get('/rooms/{room}', function (Request $req) {
    $room = 'room.' . $req->param('room');
    return Response::websocket(
        function (WebSocket $ws) use ($room) {
            $ws->subscribe($room);
            while (($m = $ws->receive()) !== null) {
                Topic::publish($room, $m->data);
            }
        });
})->noTimeout();
""")],
    lanes=[Lane("cli", "Browsers", "go", "one socket each"),
           Lane("t1", "PHP thread 1", "php", "a fiber per socket"),
           Lane("topic", "Go · topic room.42", "queue", "hands out in order")],
    tokens=[Tok("W1", "ws 1", 0), Tok("W2", "ws 2", 1), Tok("W3", "ws 3", 2), Tok("msg", "hi", 4, True),
            Tok("c1", "hi", 4, True), Tok("c2", "hi", 4, True), Tok("c3", "hi", 4, True)],
    marks=[Mark("subs", "subscribers: ws 1, ws 2, ws 3", "topic", 2, "nile"),
           Mark("quiet", "they do not run", "t1", 3.75, "muted")],
    steps=[
        Step("Three browsers open the room. Each handshake runs the route's handler, and the socket's function runs in the request's fiber.",
             lines=["Response::websocket"], at={"W1": ("t1", 0), "W2": ("t1", 1.65), "W3": ("t1", 2.6)}),
        Step("Each socket subscribes to the room and waits in `receive()`. Waiting sockets hold no thread: one PHP thread holds as many as it has clients.",
             lines=["subscribe(", "receive()"], at={"W1": ("t1", 0, "wait"), "W2": ("t1", 1.65, "wait"), "W3": ("t1", 2.6, "wait")}, show=("subs",)),
        Step("Browser 1 sends `hi`. Go reads it ahead and wakes the fiber of ws 1.",
             lines=["receive()"], at={"msg": ("t1", 0.82), "W1": ("t1", 0)}, show=("subs",)),
        Step("`Topic::publish()` hands the message to Go in one call that waits for no client.",
             lines=["Topic::publish"], at={"msg": ("topic", 0.4)}, show=("subs",)),
        Step("Go sends it to every socket that subscribed, ws 1's too. The fibers of the other members do not run at all.",
             at={"msg": ("-",), "c1": ("cli", 0, "done"), "c2": ("cli", 1.65, "done"), "c3": ("cli", 2.6, "done"), "W1": ("t1", 0, "wait")}, show=("subs", "quiet")),
    ],
)

BLOCKING = Scene(
    id="blocking",
    title="Finding code that holds the thread",
    code=[("server.php", "php", """$app->detectBlocking(0.1);       // seconds

$http->get('/report', function () {
    $sum = 0;
    for ($i = 0; $i < 50_000_000; $i++) {
        $sum += $i % 7;          // never waits
    }
    return Response::json(['sum' => $sum]);
});
$http->get('/ping', fn () => Response::text('pong'));
""")],
    lanes=[Lane("go", "Go · watches each thread", "go"),
           Lane("t1", "PHP thread 1", "php"),
           Lane("log", "Log", "queue")],
    tokens=[Tok("A", "report", 3), Tok("B", "ping", 1)],
    marks=[Mark("over", "busy past 0.1 s: interrupt", "go", 2.6, "red"),
           Mark("line", "kept its thread 109 ms · server.php:6", "log", 2.1, "gold")],
    steps=[
        Step("`/report` runs a loop that never waits, so its fiber never gives the thread up.",
             lines=["for ($i = 0", "$sum += "], clock="0 ms", at={"A": ("t1", 0)}, lit=("t1",)),
        Step("A `/ping` arrives for the same thread. It is queued behind the loop: fibers share their thread.",
             lines=["get('/ping'"], clock="60 ms", at={"B": ("t1", 1, "queued")}, lit=("t1",)),
        Step("Go watches the threads. When a fiber has held its thread past the threshold, Go interrupts the thread. The check costs nothing in PHP until then.",
             lines=["detectBlocking(0.1)"], clock="100 ms", at={}, show=("over",), lit=("go",)),
        Step("At its next safe point the fiber logs once how long it held the thread and where it was, and runs on.",
             clock="109 ms", show=("line",)),
        Step("The loop ends and `/ping` runs at last. Hooked waits yield, so they are never reported. Move such work to `offload()`.",
             lines=["return Response::json"], clock="150 ms", at={"A": ("go", 0, "done"), "B": ("t1", 1)}, show=("line",)),
    ],
)

SCENES = [HOOKS, CACHE, GRPC_STREAM, TOPICS, BLOCKING]

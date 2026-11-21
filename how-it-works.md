# How it works

1. **Declare.** `cairo serve server.php` runs the file once. `App`, `http()`,
   `get()`, `grpc()` and `service()` only record a description of the servers,
   which goes to Go.
2. **Serve.** Go opens the listeners, builds the router and compiles the
   `.proto` files (no `protoc` needed). It starts the PHP request threads and
   the offload threads; each runs `server.php` again to build its own handlers.
3. **One request, one fiber.** Go accepts a request and sends it to a request
   thread: one that is running PHP and will take it within microseconds when
   there is one, else the least busy (the fewest requests in flight, passing
   over a thread whose PHP has run one fiber for 5 ms or more without
   pausing). There it starts in a new Fiber, and when the handler waits, only
   that fiber suspends.
   - **Waits that need nothing of Go stay on the PHP thread.** The thread
     keeps the timers of `Cairo\sleep()`, channels and `select()` itself, and
     watches the sockets of PHP's own functions (streams, PDO MySQL, curl) in
     an epoll of its own. No goroutine is involved, and a sleep or a
     hand-over between two fibers costs about a microsecond.
   - **What Cairo does in Go runs there for the length of the operation**: a
     PostgreSQL query, the HTTP, gRPC and network clients, DNS, connects and
     TLS. The operation gets a goroutine and the request's
     `context.Context`, narrowed to the deadline of the context that asked,
     and its result wakes the fiber.
   - `Cairo\async()` starts a child fiber on the same thread, with a child
     context. Both are PHP alone: Go has no goroutine and no context for a
     fiber.
   - A thread with nothing to run sleeps, and Go wakes it when it queues a
     request or a result for it. Neither side calls the other for that.
4. **CPU work.** `Cairo\offload('fn', ...$args)` runs a function on the offload
   pool, so a heavy computation never stalls the fibers on a request thread.
   Code cannot move between PHP threads, so pass a function name or
   `[Class::class, 'staticMethod']`, with serializable arguments, or a
   `Cairo\OffloadTask` object: it is serialized with its input, and its
   `run()` runs on an offload thread (`offload(new Thumbnail($path, 200))`).
   The job goes from its request thread straight to the offload thread with
   the least to do, and its result straight back; an empty job takes about
   35 µs, so `offload()` is for work that takes longer than that.
   A job that throws raises `Cairo\OffloadException` naming the original
   exception class. So does a result that cannot be serialized, and a job
   whose offload thread stopped while it ran.

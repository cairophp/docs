# How it works

1. **Declare.** `cairo serve server.php` runs the file once. `App`, `http()`,
   `get()`, `grpc()` and `service()` only record a description of the servers,
   which goes to Go.
2. **Serve.** Go opens the listeners, builds the router and compiles the
   `.proto` files (no `protoc` needed). It starts the PHP request threads and
   the offload threads; each runs `server.php` again to build its own handlers.
3. **One fiber, one goroutine.** Go accepts a request on a goroutine and sends
   it to the least busy request thread (the fewest requests in flight,
   passing over a thread whose PHP has run one fiber for 5 ms or more without
   pausing), where it starts in a new Fiber. That
   goroutine owns the request's `context.Context`. When the handler calls a
   Cairo I/O function such as `Cairo\sleep()`, the fiber suspends, the
   goroutine performs the operation, then wakes the fiber. `Cairo\async()`
   starts a child fiber with its own child goroutine and child context.
4. **CPU work.** `Cairo\offload('fn', ...$args)` runs a function on the offload
   pool, so a heavy computation never stalls the fibers on a request thread.
   Code cannot move between PHP threads, so pass a function name or
   `[Class::class, 'staticMethod']`, with serializable arguments, or a
   `Cairo\OffloadTask` object: it is serialized with its input, and its
   `run()` runs on an offload thread (`offload(new Thumbnail($path, 200))`).
   A job that throws raises `Cairo\OffloadException` naming the original
   exception class.

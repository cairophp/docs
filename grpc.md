# gRPC

`cairo gen` turns `.proto` files into PHP: a class per message (typed
properties, a named-argument constructor, `fromArray()` / `toArray()`), a class
of constants per enum, and per service an interface to implement and a typed
client. It needs no `protoc` and no `google/protobuf` runtime.

```sh
cairo gen --out gen proto/helloworld.proto     # -I DIR for imports
```

```php
require __DIR__ . '/gen/autoload.php';

final class Greeter implements Helloworld\GreeterInterface
{
    public function SayHello(HelloRequest $request, Cairo\Context $ctx): HelloReply
    {
        if ($request->name === '') {
            throw new Cairo\Grpc\Exception(Cairo\Grpc\Code::INVALID_ARGUMENT, 'name is required');
        }
        return new HelloReply(message: "Hello {$request->name}");
    }
}
```

Go reads each call with the method's descriptor and passes it to PHP as an
array in protojson's shape; when a handler's first parameter is a generated
class, Cairo builds it with `fromArray()`, and a returned object goes back
through `toArray()`. Handlers that take and return plain arrays keep working.

The array is written straight from the message's bytes, and a reply is read
back into bytes the same way: no message object and no JSON text in between.
A message that holds a `google.protobuf` well-known type, a message of a
proto2 file, and a value in one of the looser forms that protojson reads (a
number given as a string for a 32-bit field, say) take the longer way through
protojson itself. The result is the same either way; only the cost differs,
about 0.15 µs against 2.5 µs for a small message. A reply that is no message
of the method's type (a field of the wrong type, or a field the message
does not have) ends its call with INTERNAL.

Mapping: properties use the protojson (lowerCamelCase) field names; 64-bit
integers are PHP `int`; `bytes` are raw strings; enums are `int` with
constants; `optional` and `oneof` fields are nullable; nested types are
`Outer_Inner`; `google.protobuf.*` well-known types stay in their protojson
form (a string for `Timestamp`).

Streaming methods get a `Cairo\Grpc\ServerStream`. Server streaming handlers
take `(request, stream, ctx)` and `send()` their replies; client-streaming
and bidirectional ones take `(stream, ctx)` and `recv()` (or `foreach`) the
client's messages until `null`. A client-streaming handler returns its reply,
and an exception ends the stream with its status:

```php
public function CountUp(CountRequest $request, ServerStream $stream, Cairo\Context $ctx): void
{
    for ($i = 1; $i <= $request->count; $i++) {
        $stream->send(new HelloReply(message: "{$request->name} $i"));
    }
}

public function Chat(ServerStream $stream, Cairo\Context $ctx): void
{
    foreach ($stream as $request) {           // HelloRequest objects
        $stream->send(new HelloReply(message: "Hello {$request->name}"));
    }
}
```

`send()` queues the reply for Go to write with one call and returns without
a fiber switch; once 64 replies are waiting, it waits for room. Queued replies reach
the client before the call's status, and a write that failed (the client went
away) is thrown by the next `send()`.

Go reads the client's messages ahead of the handler, from its first `recv()`:
64 messages or 1 MiB at most, after which the client meets HTTP/2's flow
control as it does with any reader that is slow. `recv()` waits only when
none has arrived, so a handler that reads many messages does not pay a wait
for each.

<!-- illustration: grpc-stream -->

Health checking (`grpc.health.v1`) and server reflection are built in, so
`grpcurl -plaintext localhost:9000 list` works.

To serve gRPC over TLS, give the server a certificate:
`$app->grpc(':9000')->tls($certFile, $keyFile)`. The two PEM files are read
again when they change; see [HTTPS and HTTP/2](https.md).

Calling gRPC services: the generated client carries its `.proto` descriptors,
and `Cairo\Grpc\Client` takes arrays with `.proto` files. Calls run through
grpc-go on a goroutine in Go (only the fiber waits, and the request's
deadline caps the call); connections are shared across requests and threads.

```php
$greeter = new Helloworld\GreeterClient('greeter:9000', ['timeout' => 2]);   // tls => true or [cafile, cert, key, server_name]
$reply = $greeter->SayHello(new HelloRequest(name: 'Cairo'), ['metadata' => ['x-trace' => $id]]);

$client = new Cairo\Grpc\Client('greeter:9000', ['protos' => [__DIR__ . '/proto/helloworld.proto']]);
$reply = $client->call('/helloworld.Greeter/SayHello', ['name' => 'Cairo']);       // a protojson array
$full = $client->invoke('/helloworld.Greeter/SayHello', ['name' => 'Cairo']);      // ->message, ->headers, ->trailers
```

A status other than OK throws `Cairo\Grpc\Exception` with the status code.
Streaming methods return a `Cairo\Grpc\ClientStream`:

```php
foreach ($greeter->CountUp(new CountRequest(name: 'n', count: 3)) as $reply) { ... }   // server streaming

$join = $greeter->JoinNames();                     // client streaming
$join->send(new HelloRequest(name: 'Ada'));
$reply = $join->closeAndRecv();

$chat = $greeter->Chat();                           // bidirectional
$chat->send(new HelloRequest(name: 'one'));
$reply = $chat->recv();                             // null once the server is done
$chat->closeSend();
```

`Cairo\Grpc\Client` has the same through `stream()` and `serverStream()`.
A stream keeps the request's deadline, and `close()` (or dropping the
object) cancels it.

A client's stream works like a handler's. `send()` queues the request for Go
to write and returns; once 64 are waiting, it waits for room. A request that
is no message of the method's type is refused by its own `send()`; one that
could not be written is thrown by the next `send()` or by `closeSend()`,
which returns once all that was sent is written. The status of the call
comes from `recv()`, after the replies that arrived before it. Replies are
read ahead in Go, 64 or 1 MiB at most, and `recv()` waits only when none has
arrived.

Messages cross between the client and PHP as they do in the server: straight
between protobuf's bytes and PHP's array, with protojson for the same
exceptions.

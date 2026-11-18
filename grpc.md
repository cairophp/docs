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

Go decodes each call with the method's descriptor and passes it to PHP as
protojson; when a handler's first parameter is a generated class, Cairo builds
it with `fromArray()`, and a returned object goes back through `toArray()`.
Handlers that take and return plain arrays keep working.

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

`send()` queues the reply for Go to write and returns without a fiber
switch; once 64 replies are waiting, it waits for room. Queued replies reach
the client before the call's status, and a write that failed (the client went
away) is thrown by the next `send()`.

Health checking (`grpc.health.v1`) and server reflection are built in, so
`grpcurl -plaintext localhost:9000 list` works.

Calling gRPC services: the generated client carries its `.proto` descriptors,
and `Cairo\Grpc\Client` takes arrays with `.proto` files. Calls run through
grpc-go on the fiber's goroutine (only the fiber waits, and the request's
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

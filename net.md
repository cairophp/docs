# Cairo\Net

Sockets and DNS from Go's `net` package, for protocols without a PHP client.
In a fiber only the fiber waits, and the request's deadline interrupts a
blocked read, write or accept.

```php
use Cairo\Net;

$conn = Net\dial('tcp', 'redis:6379', ['timeout' => 2]);   // also tls, unix, udp
$conn->setTimeout(5)->write("PING\r\n");
$conn->readLine("\r\n");          // "+PONG\r\n"; also read(), readExactly()

$server = Net\listen('tcp', '127.0.0.1:0');               // or 'tls' with cert/key
Cairo\async(function () use ($server) {
    $peer = $server->accept();
    while (($line = $peer->readLine()) !== null) {
        $peer->write($line);
    }
});

$udp = Net\listenPacket('udp', '0.0.0.0:0');
$udp->writeTo('ping', '10.0.0.5:9999');
[$data, $from] = $udp->readFrom(timeout: 1);

$dns = new Net\Resolver('1.1.1.1:53');                     // or the system resolver
$dns->lookupMX('example.com');   // also lookupHost/IPv4/IPv6/Addr/CNAME/TXT/NS/SRV
```

`tls` dials take the same options as PHP's `ssl` stream context. Failures
throw `Cairo\Net\NetException` with a `kind` (`dial`, `tls`, `timeout`,
`closed`, `eof`, `not_found`, ...); `TimeoutException` for timeouts.

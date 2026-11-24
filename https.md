# HTTPS and HTTP/2

Cairo can serve HTTPS itself, so one binary can face the internet with no
proxy in front of it. A server with a certificate also speaks HTTP/2 to every
client that asks for it; HTTP/1.1 clients are served as before. TLS 1.2 is the
oldest version accepted. Go's `crypto/tls` and `net/http` do the work.

There are two ways to give a server its certificate.

## Certificate files

```php
$http = $app->http(':443');
$http->tls('/etc/letsencrypt/live/example.com/fullchain.pem',
           '/etc/letsencrypt/live/example.com/privkey.pem');
```

Both files are PEM: the certificate followed by its chain, and the private
key. Cairo reads them when it starts and refuses to start when they do not
load.

The files are read again when they change, so a certificate renewed by
certbot, or a secret replaced by an orchestrator, is served without a
restart. Each handshake looks at the two files (about 2 µs, next to a
handshake of about a millisecond). When the new pair does not load, because
one file was replaced and the other not yet, the certificate in use stays
and the log says so.

## Automatic certificates

```php
$http = $app->http(':443');
$http->autoTls(['example.com', 'www.example.com'], '/var/lib/cairo/certs', email: 'ops@example.com')
     ->redirectHttp(':80');
```

Cairo asks Let's Encrypt for a certificate for each domain the first time a
client connects with that name, keeps it in the directory you name, and
renews it thirty days before it ends. Calling `autoTls()` accepts the terms
of service of the certificate authority.

What it needs:

- **The domains point to this machine**, and the authority can reach it. It
  checks a domain by connecting to it on port 443, or on port 80 when
  `redirectHttp()` listens there. Behind a load balancer that ends TLS
  itself this cannot work: use certificate files, or let the load balancer
  hold the certificate.
- **A directory that survives restarts.** It holds the account key and the
  certificates, in files only the server's user can read. In a container,
  mount a volume there. A directory that is lost on every start means a new
  certificate on every start, and Let's Encrypt limits how many it issues
  for a domain in a week.
- **One server per directory.** Several machines behind one address would
  each ask for their own certificate. Put the certificate in files, or TLS
  in the load balancer, when you run more than one.

Domains are host names; wildcards are not issued this way. A client that
asks for a name you did not list is refused during the handshake, and no
certificate is asked for.

The first request for a domain waits for its certificate, usually a few
seconds. While you try things out, pass Let's Encrypt's staging directory as
the fourth argument: its certificates are not trusted by browsers, and its
limits are far higher.

```php
$http->autoTls($domains, $dir, directory: 'https://acme-staging-v02.api.letsencrypt.org/directory');
```

The same argument takes the ACME directory of another authority, public or
your own.

## From HTTP to HTTPS

```php
$http->redirectHttp(':80');
```

adds a second listener without TLS that sends every request to the same
host, path and query on the HTTPS server, with status 308, which keeps the
method and the body. When the HTTPS server is not on port 443, the port is
part of the address it sends to. No PHP runs for a redirect. It is for a
server with `tls()` or `autoTls()`.

## HTTP/2

With a certificate there is nothing to turn on. One HTTP/2 connection
carries many requests at once, and on Cairo each of them is a fiber: a
request that waits does not hold a thread, whatever connection it came on.

Behind a load balancer or a proxy that speaks HTTP/2 to its backends without
TLS:

```php
$app->http(':8080')->h2c();
```

The server then accepts HTTP/2 from clients that start with it ("prior
knowledge", which is what load balancers do) and HTTP/1.1 on the same port.
The older `Upgrade: h2c` header is not part of it. `h2c()` is not for a
server with a certificate, which has HTTP/2 already.

## What PHP sees

```php
$req->protocol();   // "HTTP/1.1" or "HTTP/2.0"
$req->secure();     // true when the request came to Cairo over TLS
```

`$_SERVER['HTTPS']` and `SERVER_PROTOCOL` in [isolated mode](isolated-mode.md)
and the request that a [framework adapter](frameworks.md) builds say the
same. Behind a proxy that ends TLS, `secure()` is false: read the header your
proxy sets, as your framework's trusted-proxy setting does.

## gRPC

```php
$app->grpc(':9000')->tls('/etc/certs/grpc.pem', '/etc/certs/grpc-key.pem');
```

serves gRPC over TLS with a certificate from two files, read again when they
change. See [gRPC](grpc.md).

## What Cairo leaves to you

- **Compression.** Cairo does not compress responses. When it faces browsers
  directly, compress in the application, or keep a proxy or a CDN in front
  for it.
- **HTTP/3.** Not offered.
- **Client certificates** on the servers. Not offered.

`examples/https` in the Cairo repository runs each of the setups above from
environment variables.

# TLS

Cairo provides the `ssl://`, `tls://` and `tlsv1.x://` transports itself, and
an `https://` wrapper when PHP has none. Go's `crypto/tls` does the handshake
and encryption, and PHP gets a plain socket to Go, so `file_get_contents('https://…')`,
`stream_socket_client('tls://…')` and anything built on them work without
ext/openssl and suspend only the fiber. The `ssl` context options
`verify_peer`, `verify_peer_name`, `peer_name`, `SNI_server_name`,
`allow_self_signed`, `cafile`, `capath`, and client certificates through
`local_cert`, `local_pk` and `passphrase` are honoured.
`stream_socket_enable_crypto()` upgrades an open `tcp://` connection
(STARTTLS, as SMTP and IMAP clients do): Go handshakes on a goroutine
and the stream carries on over TLS. Only the client side is
offered. `stream_socket_enable_crypto($s, false)` turns TLS off again, as FTP
clients do after `CCC`: Go sends what PHP wrote, then a close_notify, waits
for the peer's (up to the stream's timeout), and the stream carries on in
clear text; it can turn TLS on again later. When PHP is built with
ext/openssl, its transports still serve code outside Cairo's fibers.

# Stability

Cairo is before 1.0. It is tested and released like a finished product, but
its PHP API is not frozen yet. This page says what a release may change, so
you can decide what to pin.

## Versions

Versions follow [Semantic Versioning](https://semver.org/):

- **A patch release** (`0.5.0` to `0.5.1`) fixes bugs. It does not change or
  remove an API.
- **A minor release** (`0.5` to `0.6`) may change or remove an API while
  Cairo is before 1.0. Every such change is in
  [CHANGELOG.md](https://github.com/cairophp/cairo/blob/main/CHANGELOG.md)
  under that release, with an "Upgrading" note that says what to use instead.
- **From 1.0 on**, only a major release may break an API.

So pin the minor version: `ghcr.io/cairophp/cairo:0.5` for the image, `^0.5`
for the stubs package (Composer treats `^0.5` as "0.5.x only"), and read the
Upgrading note before you move to the next one.

## What counts as the API

Covered by the rules above:

- The public `Cairo\` classes and functions, which are exactly what the
  [stubs package](ide.md) declares.
- The `cairo` command line: its commands, flags and environment variables.
- What `cairo gen` writes, as far as your code calls it.
- Documented behaviour of the hooked PHP functions (which calls suspend only
  their fiber).

Not covered, and free to change in any release:

- Anything under `Cairo\Internal\`.
- The Go packages (all are `internal/`) and the format in which PHP and Go
  talk to each other.
- The wording of log lines and error messages, and the fields of the
  diagnostics (slow log, heavy routes, leak and blocking reports).
- Performance numbers.

## Releases and fixes

- Fixes, security fixes included, go into the newest release only.
  [SECURITY.md](https://github.com/cairophp/cairo/blob/main/SECURITY.md) says
  how to report a vulnerability.
- There is no release calendar. A release is cut when a set of changes is
  ready, and every release passes the full test suite on amd64 and arm64,
  against MariaDB and PostgreSQL, before its binaries are published.
- The release binary and the official image carry the newest PHP that Cairo
  supports (8.5 today). A build of your own works with PHP 8.1 or newer.
- Every performance claim comes with numbers that you can rerun:
  [cairophp/benchmarks](https://github.com/cairophp/benchmarks) has the suite
  and the log of every change with its measured effect.

## What 1.0 will mean

1.0 will be tagged when two things are true: the PHP API has gone two minor
releases in a row without a breaking change, and Cairo has run real
applications in production. From then on an API is removed only in a major
release, after at least one minor release in which the changelog marks it as
deprecated.

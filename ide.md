# IDE and static analysis

The `Cairo\` classes are built into the binary, so an IDE cannot find them on
its own. `stubs/cairo.php` has the whole public API (signatures and docblocks,
no bodies) and ships as the Composer package
[cairophp/stubs](https://github.com/cairophp/stubs), a mirror of `stubs/`
published with every release. Until it is on Packagist, add the
repository and require it as a dev dependency:

```json
{
    "repositories": [{"type": "vcs", "url": "https://github.com/cairophp/stubs"}],
    "require-dev": {"cairophp/stubs": "^0.8"}
}
```

PhpStorm and Intelephense index it from `vendor/`. For PHPStan, include
`vendor/cairophp/stubs/phpstan.neon` (phpstan/extension-installer
does that for you). For Psalm, list `vendor/cairophp/stubs/cairo.php` under
`<stubs>`. The package has no autoload entry on purpose: never `require` the
stubs, since Cairo already declares these classes.

`make stubs` regenerates the file from the runtime's PHP files, and a test fails
when it is stale.

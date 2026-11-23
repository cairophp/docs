#!/usr/bin/env python3
"""Builds the Cairo landing page, docs site and logo sheet.

Usage: python3 build.py DOCS_CHECKOUT [pyramid|tower]

Reads the Markdown pages of cairophp/docs and src/, and writes two copies:
  out/pages/     full HTML documents for GitHub Pages
  out/artifact/  the same, with index.html as a body fragment for a claude.ai Artifact
The second argument picks the logo used on the pages (default: pyramid).
Needs mistune 3 and Pygments.
"""
import html
import json
import re
import sys
from pathlib import Path

import mistune
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, PhpLexer
from pygments.util import ClassNotFound

import art
import hero

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
RELEASE = "v0.5.0"
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@500;600;650;700;800'
         '&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600'
         '&family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=Figtree:wght@400;500;600;700&display=swap">')
FMT = HtmlFormatter(nowrap=True)


def hl(src: str, lang: str) -> str:
    try:
        lexer = PhpLexer(startinline=not src.startswith("<?php")) if lang == "php" else get_lexer_by_name(lang)
    except ClassNotFound:
        return html.escape(src)
    return highlight(src, lexer, FMT)


def code_block(src: str, lang: str = "") -> str:
    lang = (lang or "").strip().split()[0] if lang and lang.strip() else ""
    body = hl(src, lang) if lang else html.escape(src)
    label = f'<span class="lang">{html.escape(lang)}</span>' if lang else ""
    return (f'<div class="codeblock">{label}<button type="button" class="copy">Copy</button>'
            f'<pre class="hl"><code>{body}</code></pre></div>')


def slug(text: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", "", text)).lower()
    return re.sub(r"[^\w\- ]", "", text).strip().replace(" ", "-")


class Renderer(mistune.HTMLRenderer):
    def __init__(self, page: str):
        super().__init__(escape=False)
        self.page = page

    def block_code(self, code, info=None):
        return code_block(code, info)

    def heading(self, text, level, **attrs):
        if level == 1:
            return f"<h1>{text}</h1>\n"
        hid = f"{self.page}--{slug(text)}"
        return f'<h{level} id="{hid}">{text}<a class="anchor" href="#{hid}" aria-label="Link to this section">#</a></h{level}>\n'

    def table(self, text):
        return f'<div class="table-scroll"><table>{text}</table></div>\n'

    def link(self, text, url, title=None):
        m = re.fullmatch(r"([a-z0-9-]+)\.md(?:#([\w-]+))?", url)
        if m:
            url = f"#{m.group(1)}" + (f"--{m.group(2)}" if m.group(2) else "")
        return super().link(text, url, title)


def render(md_text: str, page: str) -> str:
    return mistune.create_markdown(renderer=Renderer(page), plugins=["table"])(md_text)


def load_docs(docs: Path):
    """Returns the overview text and the nav groups [(group, [(id, title)])] from README.md."""
    readme = (docs / "README.md").read_text().split("## Changing these pages")[0]
    groups, current = [], None
    for line in readme.splitlines():
        if line.startswith("## "):
            current = (line[3:].strip(), [])
            groups.append(current)
        m = re.match(r"- \[(.+)\]\(([a-z0-9-]+)\.md\)", line)
        if m and current:
            current[1].append((m.group(2), m.group(1)))
    return readme, groups


def fix_source(page: str, text: str) -> str:
    # install.md still names v0.2.0; the README of cairophp/cairo and the latest release say the latest release.
    return text.replace("v0.2.0", RELEASE) if page == "install" else text


def logo_svg(name: str) -> str:
    svg = (SRC / "logos" / f"{name}.svg").read_text()
    svg = re.sub(r"<metadata>.*?</metadata>", "", svg, flags=re.S)  # provenance data the file store adds
    svg = svg.replace(' xmlns:c2pa="http://c2pa.org/manifest"', "")
    svg = re.sub(r"<!--.*?-->\s*", "", svg, flags=re.S)
    svg = re.sub(r"<title>.*?</title>\s*", "", svg)
    svg = svg.replace('role="img" aria-label="Cairo"', 'aria-hidden="true" focusable="false"')
    return " ".join(svg.split())


GROUP_ICONS = {"Start": "bolt", "Serving": "globe", "Concurrency": "branch", "Data and I/O": "db",
               "Running applications": "shield", "Tooling": "code"}


def build_docs(docs: Path, logo: str) -> str:
    readme, groups = load_docs(docs)
    order = [("overview", "Overview", "Start")] + [(p, t, g) for g, items in groups for p, t in items]
    sections, index = [], []
    for i, (pid, title, group) in enumerate(order):
        src_name = "README.md" if pid == "overview" else f"{pid}.md"
        text = readme if pid == "overview" else fix_source(pid, (docs / src_name).read_text())
        body = render(text, pid)
        pager = '<nav class="pager" aria-label="Pages">'
        if i > 0:
            pager += f'<a class="prev" href="#{order[i - 1][0]}"><small>← Previous</small>{html.escape(order[i - 1][1])}</a>'
        if i + 1 < len(order):
            pager += f'<a class="next" href="#{order[i + 1][0]}"><small>Next →</small>{html.escape(order[i + 1][1])}</a>'
        pager += "</nav>"
        sections.append(f'<article class="page" data-id="{pid}" data-src="{src_name}" data-title="{html.escape(title)}">'
                        f'<p class="crumb">{html.escape(group)}</p>{body}{pager}</article>')
        plain = re.sub(r"</(p|li|h\d|pre|td|th|tr|ul|ol)>|<br\s*/?>|\n", " ", body)
        plain = re.sub(r'<a class="anchor"[^>]*>#</a>|<button[^>]*>.*?</button>|<span class="lang">.*?</span>|<[^>]+>', "", plain)
        index.append({"id": pid, "title": title, "text": " ".join(html.unescape(plain).split())})

    nav = []
    for gi, (group, items) in enumerate(groups):
        if gi == 0:
            items = [("overview", "Overview")] + items
        links = "".join(f'<li><a href="#{pid}">{html.escape(t)}</a></li>' for pid, t in items)
        nav.append(f"<h4>{art.icon(GROUP_ICONS.get(group, 'bolt'))}{html.escape(group)}</h4><ul>{links}</ul>")

    tpl = (SRC / "docs.html").read_text()
    for name in ("menu", "search", "github", "theme", "edit"):
        tpl = tpl.replace("{{ICON_%s}}" % name.upper(), art.icon(name))
    return (tpl.replace("{{LOGO}}", logo_svg(logo)).replace("{{NAV}}", "".join(nav))
               .replace("{{PAGES}}", "".join(sections))
               .replace("{{INDEX}}", json.dumps(index, ensure_ascii=False).replace("</", "<\\/")))


BENCH = {  # requests/s, 2026-11-21, one machine: fullbench-2026-11-19/rerun-2026-11-21/README.md
    "servers": ["Cairo", "Swoole", "ReactPHP", "Amp", "FrankenPHP", "RoadRunner", "nginx + FPM"],
    "rows": {
        "hello": [49706, 153997, 34916, 13282, 11485, 11470, 10828],
        "json": [51162, 161837, 34030, 13672, 11353, 11478, 11395],
        "cpu": [3996, 5151, 4520, 3886, 2973, 3519, 3357],
        "sleep": [11990, 12129, 12127, 11064, 1968, 1933, 1939],
        "curl": [11267, 11010, 6381, 2612, 1890, 1857, 1839],
        "pgsql": [19033, 15058, 9684, 6574, 4944, 6484, 6370],
        "mysql": [26403, 37091, 8933, 3971, 6895, 9241, 7845],
    },
}


def bench_parts():
    head = "".join(f'<th scope="col"{" class=me" if s == "Cairo" else ""}>{html.escape(s)}</th>' for s in BENCH["servers"])
    rows = []
    for case, vals in BENCH["rows"].items():
        best = max(vals)
        cells = "".join(f'<td class="{"me " if i == 0 else ""}{"best" if v == best else ""}">{v:,}</td>' for i, v in enumerate(vals))
        rows.append(f"<tr><td>{case}</td>{cells}</tr>")
    sleep = BENCH["rows"]["sleep"]
    top = max(sleep)
    bars = "".join(
        f'<div class="bar{" me" if s == "Cairo" else ""}"><span>{html.escape(s)}</span>'
        f'<span class="track"><span class="fill" style="width:{v / top * 100:.1f}%"></span></span>'
        f'<span class="val">{v:,}</span></div>' for s, v in zip(BENCH["servers"], sleep))
    return head, "".join(rows), bars


CODE_HTTP = """<?php // server.php
use Cairo\\App;
use Cairo\\Http\\{Request, Response};
use function Cairo\\{sleep, offload};

$app = new App();
$app->threads('auto');          // request threads; each runs many fibers
$app->offloadThreads('auto');   // CPU threads for Cairo\\offload()

$http = $app->http(':8080');
$http->get('/hello/{name}', fn (Request $r) => Response::text("Hello {$r->param('name')}\\n"));
$http->get('/slow', function (): Response {
    sleep(1);                    // only this fiber suspends
    return Response::json(['ok' => true]);
});
$http->get('/report', fn () => Response::json(offload('buildReport', 2026)));

$grpc = $app->grpc(':9000')->proto(__DIR__ . '/proto/helloworld.proto');
$grpc->service('helloworld.Greeter', Greeter::class);

return $app;
"""

CODE_GRPC = """<?php // cairo gen --out gen proto/helloworld.proto
require __DIR__ . '/gen/autoload.php';

final class Greeter implements Helloworld\\GreeterInterface
{
    public function SayHello(HelloRequest $request, Cairo\\Context $ctx): HelloReply
    {
        if ($request->name === '') {
            throw new Cairo\\Grpc\\Exception(Cairo\\Grpc\\Code::INVALID_ARGUMENT, 'name is required');
        }
        return new HelloReply(message: "Hello {$request->name}");
    }

    public function Chat(ServerStream $stream, Cairo\\Context $ctx): void
    {
        foreach ($stream as $request) {           // HelloRequest objects
            $stream->send(new HelloReply(message: "Hello {$request->name}"));
        }
    }
}
"""

CODE_ASYNC = """<?php
use function Cairo\\{async, await, all, offload};

$http->get('/dashboard/{id}', function (Request $r, Context $ctx): Response {
    $id = (int) $r->param('id');

    // each async() is a fiber of its own on this thread: the waits overlap
    [$user, $orders] = await(all([
        async(fn () => fetchUser($id)),
        async(fn () => fetchOrders($id)),
    ]));

    // CPU-heavy work goes to the offload threads
    $chart = offload('renderChart', $orders);

    return Response::json(['user' => $user, 'orders' => $orders, 'chart' => $chart]);
});
"""

CODE_CHAN = """<?php
use Cairo\\Channel;
use function Cairo\\{async, select};

$jobs = new Channel(100);
async(function () use ($jobs, $ids) {
    foreach ($ids as $id) {
        $jobs->send($id);
    }
    $jobs->close();
});

[$key, $value, $ok] = select([
    'job'  => $jobs,                // receive
    'out'  => [$results, $row],     // send
    'done' => $ctx->done(),         // closed when the request's context ends
], timeout: 0.5);
"""

INSTALL_BIN = f"""curl -fsSLO https://github.com/cairophp/cairo/releases/download/{RELEASE}/cairo-linux-amd64
install -m 755 cairo-linux-amd64 /usr/local/bin/cairo
cairo serve server.php
"""

INSTALL_DOCKER = """FROM scratch
COPY cairo-linux-amd64 /cairo
COPY . /app
WORKDIR /app
ENTRYPOINT ["/cairo", "serve", "server.php"]
"""

INSTALL_OCTANE = """composer require laravel/octane cairophp/octane
php artisan octane:start --server=cairo
"""

CODE_OCTANE = """composer require laravel/octane cairophp/octane
php artisan octane:start --server=cairo

# several requests per thread while others wait on I/O
php artisan octane:cairo --mode=fibers --concurrency=8 --detect-leaks
"""


def panel(src: str, lang: str) -> str:
    return f'<button type="button" class="copy">Copy</button><pre class="hl"><code>{hl(src, lang)}</code></pre>'


def build_landing(logo: str) -> str:
    head, rows, bars = bench_parts()
    lg = logo_svg(logo)
    out = (SRC / "landing.html").read_text()
    parts = {
        "LOGO": lg, "LOGO_BIG": lg, "SCENE": hero.scene(), "DIAGRAM": art.diagram(), "CARDS": art.cards_html(),
        "ICON_GITHUB": art.icon("github"), "ICON_ARROW": art.icon("arrow"), "ICON_BOLT": art.icon("bolt"),
        "INSTALL_BIN": panel(INSTALL_BIN, "sh"), "INSTALL_DOCKER": panel(INSTALL_DOCKER, "dockerfile"),
        "INSTALL_OCTANE": panel(INSTALL_OCTANE, "sh"),
        "CODE_HTTP": panel(CODE_HTTP, "php"), "CODE_GRPC": panel(CODE_GRPC, "php"),
        "CODE_ASYNC": panel(CODE_ASYNC, "php"), "CODE_CHAN": panel(CODE_CHAN, "php"),
        "CODE_OCTANE": panel(CODE_OCTANE, "sh"),
        "BENCH_HEAD": head, "BENCH_ROWS": rows, "BARS": bars,
    }
    for k, v in parts.items():
        out = out.replace("{{%s}}" % k, v)
    return out + LANDING_JS


LANDING_JS = """<script>
(function () {
  document.querySelectorAll('[role="tablist"]').forEach(function (list) {
    var tabs = list.querySelectorAll('[role="tab"]');
    tabs.forEach(function (t) {
      t.addEventListener('click', function () {
        tabs.forEach(function (o) {
          var on = o === t;
          o.setAttribute('aria-selected', on ? 'true' : 'false');
          document.getElementById(o.getAttribute('aria-controls')).hidden = !on;
        });
      });
    });
  });
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.copy');
    if (!b) return;
    var text = b.parentNode.querySelector('pre').innerText;
    try { navigator.clipboard.writeText(text).then(function () { b.textContent = 'Copied'; setTimeout(function () { b.textContent = 'Copy'; }, 1500); }, function () {}); } catch (err) {}
  });
  if (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('.scene animate, .scene animateMotion').forEach(function (a) { a.remove(); });
    var r = document.querySelector('.scene .reqs'); if (r) r.remove();
  }
})();
</script>"""


def build_logos() -> str:
    tiles = []
    for name, title, idea in (
        ("stack", "New 1: Stacked courses",
         "A pyramid of four courses, one per PHP thread. The third course, in Nile teal, has slid east: a fiber moving on while the others wait."),
        ("ring", "New 2: The tower in a C",
         "Cairo Tower, flat and teal, standing inside a gold C. It reads as a badge at any size and spells the name without letters."),
        ("sunrise", "New 3: Sunset behind the pyramid",
         "Two shapes only: the oldest skyline of Cairo. The flattest of the six, good for a favicon and for stickers."),
        ("lettermark", "New 4: The C with a pyramid inside",
         "An app-icon lettermark: a bold C on a desert-gold tile, its counter cut as a pyramid."),
        ("pyramid", "Earlier: The pyramid",
         "A pyramid lit from the east, with a teal crescent for the C of Cairo."),
        ("tower", "Earlier: Cairo Tower",
         "The lotus-topped tower: a lattice shaft, the lotus crown and a mast light."),
    ):
        svg = logo_svg(name).replace('aria-hidden="true" focusable="false"', f'role="img" aria-label="Cairo logo, {name}"')
        tiles.append(f'''<section class="idea"><h2>{title}</h2><p>{idea}</p>
<div class="row"><div class="tile dark">{svg}</div><div class="tile light">{svg}</div>
<div class="small"><div class="lockup dark">{svg}<span>Cairo</span></div><div class="lockup light">{svg}<span>Cairo</span></div>
<div class="sizes">{svg}{svg}{svg}</div></div></div>
<p class="file">Source: <code>src/logos/{name}.svg</code></p></section>''')
    return f'''<header class="hd"><a href="index.html">← Cairo</a><h1>Logo ideas</h1><p>Six directions, each a small flat SVG shown on dark and light, beside the wordmark and at 16, 32 and 64 px. Pick one and the site switches to it with one build flag.</p></header>
<main>{"".join(tiles)}</main>
<style>
:root {{ --bg: #080A13; --ink: #EEF0F8; --muted: #9EA5BE; --line: rgba(220,226,255,.12); color-scheme: dark; }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.6 Inter, system-ui, sans-serif; }}
.hd, main {{ max-width: 64rem; margin: 0 auto; padding-left: max(20px, env(safe-area-inset-left, 0px)); padding-right: max(20px, env(safe-area-inset-right, 0px)); }}
.hd {{ padding-block: 3rem 1rem; }} .hd a {{ color: #61D8CB; text-decoration: none; }}
h1, h2 {{ font-family: Sora, system-ui, sans-serif; letter-spacing: -0.03em; margin: 0.4rem 0; }}
h1 {{ font-size: clamp(2rem, 5vw, 3rem); }} .hd p, .idea > p {{ color: var(--muted); max-width: 44rem; }}
.idea {{ border-top: 1px solid var(--line); padding-block: 2.5rem; }}
.row {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; margin-top: 1.5rem; }}
.tile {{ border-radius: 28px; aspect-ratio: 1; display: grid; place-items: center; max-width: 100%; }}
.tile svg {{ width: 70%; height: 70%; }}
.dark {{ background: radial-gradient(circle at 50% 30%, #1A1F45, #0B0D1A); border: 1px solid var(--line); }}
.light {{ background: #F6F3EC; color: #141829; }}
.small {{ display: grid; gap: 1rem; align-content: start; }}
.lockup {{ border-radius: 18px; display: flex; align-items: center; gap: .7rem; padding: 1rem 1.2rem; font: 700 1.6rem Sora, system-ui, sans-serif; letter-spacing: -0.03em; }}
.lockup svg {{ width: 48px; height: 48px; }}
.sizes {{ display: flex; align-items: end; gap: 1rem; padding: 1rem 1.2rem; border: 1px solid var(--line); border-radius: 18px; }}
.sizes svg:nth-child(1) {{ width: 16px; height: 16px; }} .sizes svg:nth-child(2) {{ width: 32px; height: 32px; }} .sizes svg:nth-child(3) {{ width: 64px; height: 64px; }}
.file {{ font-size: .85rem; }} code {{ font-family: "JetBrains Mono", monospace; color: #FFD996; }}
@media (max-width: 720px) {{ .row {{ grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }} .small {{ grid-column: 1 / -1; }} }}
</style>'''


def head(title: str, desc: str, css: str, logo: str, fragment: bool) -> str:
    meta = (f'<title>{title}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            f'<meta name="description" content="{html.escape(desc)}">\n'
            f'<link rel="icon" href="{logo}.svg" type="image/svg+xml">\n{FONTS}\n<style>{css}</style>\n')
    if fragment:
        return meta
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'{meta}</head>\n<body>\n')


def main():
    docs = Path(sys.argv[1])
    logo = sys.argv[2] if len(sys.argv) > 2 else "pyramid"
    landing = build_landing(logo)
    docs_body = build_docs(docs, logo)
    logos = build_logos()
    landing_css = (SRC / "landing.css").read_text()
    docs_css = (SRC / "docs.css").read_text()
    ldesc = "Cairo is a PHP application server in one Go binary: HTTP and gRPC declared in PHP, every request in its own fiber."
    end = "</body>\n</html>\n"
    for name, fragment in (("pages", False), ("artifact", True)):
        out = ROOT / "out" / name
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(head("Cairo", ldesc, landing_css, logo, fragment) + landing + ("" if fragment else end))
        (out / "docs.html").write_text(head("Cairo Docs", "Documentation for Cairo, the PHP application server in one Go binary.", docs_css, logo, False) + docs_body + end)
        (out / "logos.html").write_text(head("Cairo Logos", "Logo ideas for Cairo.", "", logo, False) + logos + end)
        for n in ("pyramid", "tower", "stack", "ring", "sunrise", "lettermark"):
            (out / f"{n}.svg").write_text((SRC / "logos" / f"{n}.svg").read_text())
        stale = out / "logo.svg"
        if stale.exists():
            stale.unlink()
    print("built", ROOT / "out", "with the", logo, "logo")


if __name__ == "__main__":
    main()

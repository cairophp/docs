"""Inline SVG for the Cairo site: icons, the hero scene and the request diagram."""
import random

_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>'

ICONS = {
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "bolt": '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    "github": '<path fill="currentColor" stroke="none" d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.1-1.47-1.1-1.47-.9-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.52 2.34 1.08 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02a9.6 9.6 0 0 1 5 0c1.91-1.3 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.69-4.57 4.93.36.31.68.92.68 1.85v2.75c0 .27.18.58.69.48A10 10 0 0 0 12 2z"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "theme": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "edit": '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/>',
    "swap": '<path d="M4 8h14l-4-4M20 16H6l4 4"/>',
    "code": '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14"/>',
    "hook": '<path d="M9 3v10a4 4 0 0 0 8 0v-2"/><path d="m14 13 3-3 3 3"/>',
    "branch": '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="9" r="2"/><path d="M6 7v10M18 11c0 4-6 3-11 6"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "cpu": '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    "db": '<ellipse cx="12" cy="5.5" rx="7" ry="2.5"/><path d="M5 5.5v13c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-13M5 12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5"/>',
    "layers": '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    "zap": '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    "shield": '<path d="M12 3 4 6v6c0 4.5 3.4 8 8 9 4.6-1 8-4.5 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
    "pulse": '<path d="M3 12h4l3-7 4 14 3-7h4"/>',
    "box": '<path d="m12 2 9 5v10l-9 5-9-5V7z"/><path d="m3 7 9 5 9-5M12 12v10"/>',
    "lock": '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
}


def icon(name: str) -> str:
    return _ICON.format(ICONS[name])


CARDS = [
    ("globe", "HTTP server", "Routes, middleware, uploads and TLS on Go's net/http, declared from PHP.", "middleware", "Middleware"),
    ("swap", "gRPC, no protoc", "Unary and streaming calls, health checks and reflection. <code>cairo gen</code> writes typed classes and clients.", "grpc", "gRPC"),
    ("hook", "Your PHP, hooked", "<code>sleep()</code>, streams, PDO MySQL, curl and DNS pause only their fiber. Libraries get concurrency without a rewrite.", "runtime-hooks", "Runtime hooks"),
    ("branch", "async, await, channels", "Run I/O in parallel with <code>async()</code>, pass values with channels, wait on several with <code>select()</code>.", "concurrency", "Concurrency API"),
    ("clock", "Deadlines that reach I/O", "Every request carries a context. Timeouts and cancellation stop the query or call that is waiting.", "context", "Context and deadlines"),
    ("cpu", "Offload pool", "<code>Cairo\\offload()</code> runs CPU-heavy work on its own threads and hands the result back to the fiber.", "concurrency", "Offload"),
    ("db", "PostgreSQL and MySQL", "PHP's <code>pdo_pgsql</code> on libpq, PDO MySQL and mysqli, each wait on the fiber.", "postgresql", "Databases"),
    ("layers", "Connection pools", "<code>Cairo\\Pool</code> shares connections between fibers, with wait timeouts, resets and lifetimes.", "pools", "Pools"),
    ("zap", "Response cache", "Go answers repeated GETs from memory without running PHP, with stale-while-revalidate and tags.", "response-cache", "Response cache"),
    ("shield", "Isolated mode", "Code that needs <code>$_GET</code>, <code>echo</code> or singletons gets one request per thread and a clean state after.", "isolated-mode", "Isolated mode"),
    ("pulse", "Finds what blocks", "Logs for blocking calls, slow requests with where they waited, heavy routes and leaking statics.", "blocking", "Diagnostics"),
    ("box", "One static binary", "PHP 8.5, opcache and the extensions linked in with musl, for amd64 and arm64. Runs <code>FROM scratch</code>.", "building", "Building"),
]


def cards_html() -> str:
    out = []
    for ic, title, text, page, link in CARDS:
        out.append(f'<article class="card"><div class="ic">{icon(ic)}</div><h3>{title}</h3><p>{text}</p>'
                   f'<a href="docs.html#{page}">{link} →</a></article>')
    return "".join(out)


def _pyramid(apex, left, right, front_x, lit, shade):
    ax, ay = apex
    return (f'<polygon points="{ax},{ay} {left[0]},{left[1]} {front_x},{left[1] + 4}" fill="url(#{shade})"/>'
            f'<polygon points="{ax},{ay} {front_x},{left[1] + 4} {right[0]},{right[1]}" fill="url(#{lit})"/>')


def scene() -> str:
    rnd = random.Random(7)
    stars = []
    for i in range(80):
        x, y, r = rnd.uniform(0, 1200), rnd.uniform(0, 250) ** 1.08 / 1.5, rnd.choice([0.6, 0.8, 1, 1.3])
        cls = ' class="twinkle"' if i % 5 == 0 else ""
        delay = f' style="animation-delay:{rnd.uniform(0, 3):.1f}s"' if cls else ""
        stars.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#fff" opacity="{rnd.uniform(0.35, 0.9):.2f}"{cls}{delay}/>')
    # far skyline: blocks, domes and minarets
    sky = []
    x = 640
    while x < 1200:
        w, h = rnd.randint(18, 46), rnd.randint(14, 48)
        sky.append(f'<rect x="{x}" y="{340 - h}" width="{w}" height="{h}"/>')
        if rnd.random() < 0.22:
            sky.append(f'<path d="M{x + w / 2 - 9} {340 - h} a9 9 0 0 1 18 0z"/><rect x="{x + w / 2 - 1.5}" y="{340 - h - 34}" width="3" height="26"/>')
        x += w + rnd.randint(0, 6)
    lights = "".join(f'<rect x="{rnd.randint(650, 1190)}" y="{rnd.randint(305, 336)}" width="2" height="2" fill="#F7BE55" opacity="{rnd.uniform(.4, .9):.2f}"/>' for _ in range(40))
    lattice = "".join(f'<path d="M860 {y} L940 {y + 40} M940 {y} L860 {y + 40}"/>' for y in range(120, 360, 16))
    reqs = "".join(
        f'<circle r="3.2" fill="{c}" filter="url(#glow)"><animateMotion dur="7s" begin="{d}s" repeatCount="indefinite" path="M-20 372 C 220 356, 420 388, 640 370 S 1000 356, 1220 372"/></circle>'
        for d, c in [(0, "#F7BE55"), (1.3, "#61D8CB"), (2.4, "#F7BE55"), (3.6, "#F07F3A"), (4.7, "#61D8CB"), (5.9, "#F7BE55")])
    return f'''<svg viewBox="0 0 1200 420" preserveAspectRatio="xMidYMax slice" role="presentation">
<defs>
 <linearGradient id="g-lit" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFD98A"/><stop offset="1" stop-color="#E8873A"/></linearGradient>
 <linearGradient id="g-shade" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#B85A22"/><stop offset="1" stop-color="#5E2A16"/></linearGradient>
 <linearGradient id="g-lit2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#E9B26A"/><stop offset="1" stop-color="#B9652C"/></linearGradient>
 <linearGradient id="g-shade2" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8A431D"/><stop offset="1" stop-color="#47200F"/></linearGradient>
 <linearGradient id="g-tower" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFD98A"/><stop offset="1" stop-color="#D9692A"/></linearGradient>
 <linearGradient id="g-nile" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#123A52"/><stop offset="1" stop-color="#080A13"/></linearGradient>
 <linearGradient id="g-sand" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3A2131"/><stop offset="1" stop-color="#1A1426"/></linearGradient>
 <radialGradient id="g-halo"><stop offset="0" stop-color="#F7D58C" stop-opacity=".18"/><stop offset="1" stop-color="#F7D58C" stop-opacity="0"/></radialGradient>
 <radialGradient id="g-moon" cx=".4" cy=".4"><stop offset="0" stop-color="#FFF6DD"/><stop offset="1" stop-color="#F7D58C"/></radialGradient>
 <clipPath id="c-shaft"><path d="M890 118 L910 118 L918 344 L882 344 Z"/></clipPath>
 <mask id="m-moon"><rect width="1200" height="420" fill="#fff"/><circle cx="1012" cy="78" r="30" fill="#000"/></mask>
 <filter id="glow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<g>{"".join(stars)}</g>
<circle cx="1000" cy="90" r="34" fill="url(#g-moon)" mask="url(#m-moon)"/>
<circle cx="1000" cy="90" r="90" fill="url(#g-halo)"/>
<g fill="#161B3D">{"".join(sky)}</g>
{lights}
<path d="M0 340 L1200 340 L1200 360 L0 360 Z" fill="url(#g-sand)"/>
{_pyramid((612, 262), (548, 342), (688, 340), 628, "g-lit2", "g-shade2")}
{_pyramid((468, 196), (356, 342), (600, 338), 498, "g-lit2", "g-shade2")}
{_pyramid((250, 120), (60, 344), (470, 338), 300, "g-lit", "g-shade")}
<g>
 <line x1="900" y1="40" x2="900" y2="78" stroke="#61D8CB" stroke-width="2"/>
 <circle cx="900" cy="40" r="3.5" fill="#F06A5A" filter="url(#glow)"><animate attributeName="opacity" values="1;.2;1" dur="2.4s" repeatCount="indefinite"/></circle>
 <path d="M900 78 C 888 86, 884 98, 886 110 L 914 110 C 916 98, 912 86, 900 78 Z" fill="url(#g-tower)"/>
 <path d="M886 110 C 874 106, 868 96, 868 86 C 877 90, 883 98, 888 106 Z" fill="#C9672B"/>
 <path d="M914 110 C 926 106, 932 96, 932 86 C 923 90, 917 98, 912 106 Z" fill="#A9521F"/>
 <rect x="878" y="109" width="44" height="7" rx="3" fill="url(#g-tower)"/>
 <rect x="886" y="116" width="28" height="4" fill="#B85A22"/>
 <path d="M890 118 L910 118 L918 344 L882 344 Z" fill="url(#g-tower)"/>
 <path d="M900 118 L910 118 L918 344 L900 344 Z" fill="#7A3214" opacity=".45"/>
 <g clip-path="url(#c-shaft)" stroke="#6E2A10" stroke-width="1.2" opacity=".6">{lattice}</g>
 <path d="M872 344 L928 344 L934 352 L866 352 Z" fill="#8A431D"/>
</g>
<path d="M0 356 L1200 356 L1200 420 L0 420 Z" fill="url(#g-nile)"/>
<g stroke="#61D8CB" stroke-linecap="round" opacity=".22">
 <path d="M80 384h90M260 398h60M520 388h120M760 402h70M930 384h110M1080 396h60" stroke-width="2"/>
 <path d="M884 364h32M890 372h20M893 380h14" stroke="#F7BE55" stroke-width="2"/>
 <path d="M200 364h100M230 372h40" stroke="#F7BE55" stroke-width="2"/>
</g>
<path d="M-20 372 C 220 356, 420 388, 640 370 S 1000 356, 1220 372" fill="none" stroke="#61D8CB" stroke-width="1.2" opacity=".35" stroke-dasharray="2 8"/>
<g class="reqs">{reqs}</g>
</svg>'''


def diagram() -> str:
    def thread(y, label, fibers):
        pills = []
        x = 300
        for kind, text in fibers:
            fill, ink, w = {"run": ("#F7BE55", "#1A1206", 74), "wait": ("rgba(97,216,203,.14)", "#7FE3D6", 74)}[kind]
            stroke = ' stroke="#61D8CB" stroke-opacity=".45"' if kind == "wait" else ""
            pills.append(f'<rect x="{x}" y="{y + 34}" width="{w}" height="24" rx="12" fill="{fill}"{stroke}/>'
                         f'<text x="{x + w / 2}" y="{y + 50.5}" text-anchor="middle" fill="{ink}" font-size="11" font-weight="600">{text}</text>')
            x += w + 8
        return (f'<rect x="284" y="{y}" width="300" height="74" rx="14" fill="#10142A" stroke="rgba(220,226,255,.14)"/>'
                f'<text x="300" y="{y + 22}" fill="#EEF0F8" font-size="13" font-weight="600">{label}</text>' + "".join(pills))
    return f'''<svg viewBox="0 0 600 372" role="img" aria-labelledby="dg-t">
<title id="dg-t">Go accepts requests and hands each to a fiber on a PHP thread; fibers that wait free the thread; CPU work goes to offload threads.</title>
<g font-family="Figtree, Inter, system-ui, sans-serif">
<rect x="16" y="20" width="200" height="248" rx="16" fill="rgba(97,216,203,.06)" stroke="rgba(97,216,203,.4)"/>
<text x="36" y="50" fill="#7FE3D6" font-size="13" font-weight="700" letter-spacing="1.5">GO</text>
<text x="36" y="72" fill="#9EA5BE" font-size="12">net/http and grpc-go</text>
<g font-family="JetBrains Mono, monospace" font-size="12">
<rect x="36" y="90" width="160" height="34" rx="9" fill="#0B0E1D" stroke="rgba(220,226,255,.12)"/><text x="50" y="112" fill="#EEF0F8">:8080  HTTP</text>
<rect x="36" y="134" width="160" height="34" rx="9" fill="#0B0E1D" stroke="rgba(220,226,255,.12)"/><text x="50" y="156" fill="#EEF0F8">:9000  gRPC</text>
<rect x="36" y="178" width="160" height="34" rx="9" fill="#0B0E1D" stroke="rgba(220,226,255,.12)"/><text x="50" y="200" fill="#EEF0F8">libpq · DNS · TLS</text>
</g>
<text x="36" y="246" fill="#6D7491" font-size="11">waits for PHP, never blocks it</text>
<path d="M216 112 C 250 112, 250 70, 284 70" fill="none" stroke="#F7BE55" stroke-width="1.6" stroke-dasharray="4 4"/>
<path d="M216 156 C 250 156, 250 170, 284 170" fill="none" stroke="#F7BE55" stroke-width="1.6" stroke-dasharray="4 4"/>
<circle cx="284" cy="70" r="3" fill="#F7BE55"/><circle cx="284" cy="170" r="3" fill="#F7BE55"/>
{thread(30, "PHP thread 1", [("run", "running"), ("wait", "MySQL"), ("wait", "curl")])}
{thread(130, "PHP thread 2", [("wait", "sleep"), ("run", "running"), ("wait", "gRPC")])}
<rect x="284" y="248" width="300" height="56" rx="14" fill="#10142A" stroke="rgba(240,127,58,.45)" stroke-dasharray="5 4"/>
<text x="300" y="271" fill="#F7BE55" font-size="13" font-weight="600">Offload threads</text>
<text x="300" y="290" fill="#9EA5BE" font-size="11.5">CPU work, results back to the fiber</text>
<path d="M434 204 L434 248" stroke="#F07F3A" stroke-width="1.6" stroke-dasharray="4 4"/>
<g font-size="11" fill="#9EA5BE">
<rect x="16" y="326" width="12" height="12" rx="6" fill="#F7BE55"/><text x="34" y="336">runs on the thread</text>
<rect x="160" y="326" width="12" height="12" rx="6" fill="rgba(97,216,203,.14)" stroke="#61D8CB" stroke-opacity=".45"/><text x="178" y="336">paused, waiting on I/O</text>
</g>
</g>
</svg>'''

"""The hero of the landing page: a pharaoh riding the PHP elephant at a gallop past Giza at golden hour.

One inline SVG, animated with CSS inside it (plus two SMIL path morphs for the cape and the banner).
The scenery is drawn in tiles 1200 wide, each layer twice, and slides left at its own speed.
The view box reaches 380 above the scene so the sky can run up behind the headline.
"""
import math
import random

W, H, GROUND = 1200, 420, 392  # ground: where the elephant's feet land
INK = "#141A47"

CSS = """
.h-layer { animation: h-slide linear infinite; }
@keyframes h-slide { to { transform: translateX(-1200px); } }
.h-l0 { animation-duration: 160s; } .h-l1 { animation-duration: 90s; } .h-l2 { animation-duration: 44s; } .h-l3 { animation-duration: 8s; }
.h-l4 { animation-duration: 2.4s; } .h-l5 { animation-duration: 1.3s; }
.h-rays { transform-origin: 590px 236px; animation: h-rays 70s linear infinite; }
@keyframes h-rays { to { transform: rotate(360deg); } }
.h-sunpulse { transform-origin: 590px 236px; animation: h-sunpulse 4s ease-in-out infinite alternate; }
@keyframes h-sunpulse { from { transform: scale(1); opacity: .85; } to { transform: scale(1.08); opacity: 1; } }
.h-bird { transform-box: fill-box; transform-origin: 50% 100%; animation: h-bird .5s ease-in-out infinite alternate; }
@keyframes h-bird { from { transform: scaleY(1); } to { transform: scaleY(-.35); } }
.h-glint { animation: h-glint 1.8s ease-in-out infinite; }
@keyframes h-glint { 50% { opacity: .15; } }

.h-ele { animation: h-bob .34s ease-in-out infinite alternate; }
@keyframes h-bob { from { transform: translateY(3px) rotate(1.2deg); } to { transform: translateY(-9px) rotate(-1.6deg); } }
.h-leg { transform-box: fill-box; transform-origin: 50% 6%; animation: h-leg .34s ease-in-out infinite alternate; }
@keyframes h-leg { from { transform: rotate(27deg); } to { transform: rotate(-30deg); } }
.h-leg.b { animation-delay: -.17s; } .h-leg.c { animation-delay: -.34s; } .h-leg.d { animation-delay: -.51s; }
.h-ear { transform-box: fill-box; transform-origin: 85% 20%; animation: h-ear .34s ease-in-out infinite alternate; }
@keyframes h-ear { from { transform: rotate(-14deg) scaleX(1); } to { transform: rotate(16deg) scaleX(.86); } }
.h-trunk { transform-box: fill-box; transform-origin: 0% 0%; animation: h-trunk .68s ease-in-out infinite alternate; }
@keyframes h-trunk { from { transform: rotate(-5deg); } to { transform: rotate(8deg); } }
.h-tail { transform-box: fill-box; transform-origin: 100% 0%; animation: h-tail .34s ease-in-out infinite alternate; }
@keyframes h-tail { from { transform: rotate(-22deg); } to { transform: rotate(18deg); } }
.h-rider { transform-box: fill-box; transform-origin: 50% 100%; animation: h-rider .34s ease-in-out infinite alternate; animation-delay: -.1s; }
@keyframes h-rider { from { transform: translateY(1.5px) rotate(-1deg); } to { transform: translateY(-3px) rotate(4deg); } }
.h-shadow { transform-box: fill-box; transform-origin: 50% 50%; animation: h-shadow .34s ease-in-out infinite alternate; }
@keyframes h-shadow { from { transform: scaleX(1); opacity: .34; } to { transform: scaleX(.82); opacity: .2; } }

.h-dust { transform-box: fill-box; transform-origin: 50% 50%; animation: h-dust 1.1s ease-out infinite; opacity: 0; }
@keyframes h-dust { 0% { transform: translate(0, 0) scale(.3); opacity: .95; } 100% { transform: translate(-250px, -40px) scale(2.5); opacity: 0; } }
.h-streak { animation: h-streak linear infinite; }
@keyframes h-streak { from { transform: translateX(1500px); } to { transform: translateX(-900px); } }
.h-trail { stroke-dasharray: 90 50; animation: h-trail .9s linear infinite; }
@keyframes h-trail { to { stroke-dashoffset: 140; } }
.h-spark { animation: h-spark linear infinite; opacity: 0; }
@keyframes h-spark { 0% { transform: translate(0, 0) scale(1); opacity: 1; } 100% { transform: translate(-520px, var(--dy, -20px)) scale(.2); opacity: 0; } }
.h-glow { animation: h-glow 1.4s ease-in-out infinite alternate; }
@keyframes h-glow { from { opacity: .55; } to { opacity: 1; } }
@media (max-width: 1240px) { .h-hero { transform: translate(840px, 392px) scale(.88); } }
@media (max-width: 900px) { .h-hero { transform: translate(620px, 392px) scale(.62); } .h-sun { transform: translate(-118px, -34px); } }
@media (prefers-reduced-motion: reduce) { .h-layer, .h-rays, .h-sunpulse, .h-bird, .h-glint, .h-ele, .h-leg, .h-ear, .h-trunk, .h-tail, .h-rider, .h-shadow, .h-dust, .h-streak, .h-trail, .h-spark, .h-glow { animation: none; } .h-dust, .h-spark { opacity: .5; } }
"""

DEFS = """
<linearGradient id="h-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#C6D2FF"/><stop offset=".42" stop-color="#E4DBF6"/><stop offset=".68" stop-color="#FFDDBB"/><stop offset=".88" stop-color="#FFBC7C"/><stop offset="1" stop-color="#FF9E5E"/></linearGradient>
<radialGradient id="h-halo"><stop offset="0" stop-color="#FFF6D8" stop-opacity=".95"/><stop offset=".35" stop-color="#FFE3A6" stop-opacity=".55"/><stop offset="1" stop-color="#FFD08A" stop-opacity="0"/></radialGradient>
<radialGradient id="h-sunfill" cx=".45" cy=".4"><stop offset="0" stop-color="#FFFDF2"/><stop offset="1" stop-color="#FFE08A"/></radialGradient>
<linearGradient id="h-lit" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFE09A"/><stop offset="1" stop-color="#F3A44C"/></linearGradient>
<linearGradient id="h-shade" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#D9853F"/><stop offset="1" stop-color="#A85A2B"/></linearGradient>
<linearGradient id="h-dune" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFD592"/><stop offset="1" stop-color="#F5B565"/></linearGradient>
<linearGradient id="h-sand" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F6B968"/><stop offset="1" stop-color="#E0914A"/></linearGradient>
<linearGradient id="h-body" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9CA6D4"/><stop offset="1" stop-color="#7780B6"/></linearGradient>
<linearGradient id="h-skin" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#C98D58"/><stop offset="1" stop-color="#A06236"/></linearGradient>
<linearGradient id="h-head" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9CA6D4"/><stop offset="1" stop-color="#8089BE"/></linearGradient>
<linearGradient id="h-cloth" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFC043"/><stop offset="1" stop-color="#F0702C"/></linearGradient>
<linearGradient id="h-cape" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#12B3A6"/><stop offset="1" stop-color="#12B3A6" stop-opacity=".2"/></linearGradient>
<linearGradient id="h-tr1" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>
<linearGradient id="h-tr2" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#12B3A6"/><stop offset="1" stop-color="#12B3A6" stop-opacity="0"/></linearGradient>
<linearGradient id="h-tr3" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#4F57C4"/><stop offset="1" stop-color="#4F57C4" stop-opacity="0"/></linearGradient>
<pattern id="h-nemes" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(-24)"><rect width="5" height="5" fill="#E9B24A"/><rect width="5" height="2.3" fill="#1E3A9A"/></pattern>
<filter id="h-soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.6"/></filter>
<filter id="h-bloom" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
"""


def _layer(cls: str, tile: str) -> str:
    return f'<g class="h-layer {cls}"><g>{tile}</g><g transform="translate({W})">{tile}</g></g>'


def _pyr(ax, ay, half, base, split=0.18):
    fx = ax + half * split
    return (f'<polygon points="{ax},{ay} {ax - half},{base} {fx},{base + 3}" fill="url(#h-shade)"/>'
            f'<polygon points="{ax},{ay} {fx},{base + 3} {ax + half},{base}" fill="url(#h-lit)"/>')


def _palm(x, base, h, lean=1):
    top_x, top_y = x + 14 * lean, base - h
    fronds = "".join(
        f'<path d="M{top_x} {top_y} q {dx * .5} {-abs(dx) * .35 - 10} {dx} {dy}" fill="none" stroke="{c}" stroke-width="5.5" stroke-linecap="round"/>'
        for dx, dy, c in ((-38, 10, "#1E7A5C"), (-26, -8, "#2A9A72"), (-6, -20, "#1E7A5C"), (22, -12, "#2A9A72"), (38, 8, "#1E7A5C"), (30, 22, "#176349"), (-30, 24, "#176349")))
    return (f'<path d="M{x} {base} q {4 * lean} {-h * .5} {14 * lean} {-h}" fill="none" stroke="#7A4A2E" stroke-width="7" stroke-linecap="round"/>{fronds}')


def _cloud(x, y, s=1.0, o=.9):
    return (f'<g transform="translate({x} {y}) scale({s})" fill="#fff" opacity="{o}"><ellipse cx="0" cy="0" rx="46" ry="15"/>'
            f'<ellipse cx="-20" cy="-10" rx="22" ry="15"/><ellipse cx="12" cy="-16" rx="28" ry="19"/><ellipse cx="40" cy="-4" rx="20" ry="11"/></g>')


def _birds(x, y, n, rnd):
    out = []
    for i in range(n):
        dx, dy, s = i * 26 + rnd.randint(-4, 4), (i % 2) * 12 + rnd.randint(-5, 5), rnd.uniform(.8, 1.2)
        out.append(f'<g transform="translate({x + dx} {y + dy}) scale({s:.2f})"><path class="h-bird" style="animation-delay:-{rnd.uniform(0, .5):.2f}s" '
                   f'd="M0 0 q 6 -8 12 0 q 6 -8 12 0" fill="none" stroke="{INK}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity=".7"/></g>')
    return "".join(out)


def _skyline(rnd, base):
    """The far city in the haze, with Cairo Tower."""
    out, x = [], 0
    while x < W:
        w, h = rnd.randint(16, 40), rnd.randint(8, 34)
        if rnd.random() < 0.3:
            x += rnd.randint(20, 70)
            continue
        out.append(f'<rect x="{x}" y="{base - h}" width="{w}" height="{h + 2}"/>')
        if rnd.random() < 0.22:  # a dome and a minaret
            out.append(f'<path d="M{x + w / 2 - 8} {base - h} a8 8 0 0 1 16 0z"/><rect x="{x + w / 2 - 1.5}" y="{base - h - 30}" width="3" height="24"/>')
        x += w + rnd.randint(0, 5)
    tx = 880
    out.append(f'<path d="M{tx - 5} {base - 96} L{tx + 5} {base - 96} L{tx + 8} {base} L{tx - 8} {base} Z"/>'
               f'<path d="M{tx} {base - 122} C {tx - 8} {base - 116}, {tx - 10} {base - 108}, {tx - 9} {base - 100} L {tx + 9} {base - 100} C {tx + 10} {base - 108}, {tx + 8} {base - 116}, {tx} {base - 122} Z"/>'
               f'<rect x="{tx - 13}" y="{base - 101}" width="26" height="5" rx="2"/><rect x="{tx - 1}" y="{base - 144}" width="2" height="24"/>')
    return f'<g fill="#B9789A" opacity=".55">{"".join(out)}</g>'


OUT = "#3A4479"  # the mascot's outline


def _rider() -> str:
    """The pharaoh, seated at 0,0 and facing right. A head is 22 high, so he is about seven and a half heads tall."""
    cape = ('M4 -56 C -40 -66, -74 -38, -128 -54 C -90 -34, -48 -22, -2 -30 Z',
            'M4 -56 C -38 -44, -78 -70, -134 -42 C -92 -22, -46 -36, -2 -30 Z',
            'M4 -56 C -42 -72, -70 -48, -124 -66 C -88 -48, -50 -24, -2 -30 Z')
    flag = ('M46 -112 C 30 -120, 16 -104, -4 -112 L -4 -90 C 16 -82, 30 -98, 46 -90 Z',
            'M46 -112 C 32 -104, 14 -120, -6 -108 L -6 -86 C 14 -98, 32 -82, 46 -90 Z')
    return f'''
  <path fill="url(#h-cape)" d="{cape[0]}"><animate attributeName="d" dur=".5s" repeatCount="indefinite" values="{cape[0]};{cape[1]};{cape[2]};{cape[0]}"/></path>
  <!-- far arm, raised, with the standard -->
  <path d="M13 -53 L 31 -60 L 47 -70" fill="none" stroke="#8E5630" stroke-width="7.5" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="46" y="-116" width="3" height="94" rx="1.5" fill="#E9B24A"/><circle cx="47.5" cy="-119" r="4.5" fill="#F7BE55" filter="url(#h-bloom)" class="h-glow"/>
  <path fill="#E8672B" d="{flag[0]}"><animate attributeName="d" dur=".42s" repeatCount="indefinite" values="{flag[0]};{flag[1]};{flag[0]}"/></path>
  <circle cx="47.5" cy="-70" r="4.6" fill="#8E5630"/>
  <!-- near leg -->
  <path d="M3 -3 L 31 9" fill="none" stroke="url(#h-skin)" stroke-width="14" stroke-linecap="round"/>
  <path d="M31 9 L 24 43" fill="none" stroke="url(#h-skin)" stroke-width="10.5" stroke-linecap="round"/>
  <path d="M31 9 L 25 40" fill="none" stroke="#7E4A28" stroke-width="3" stroke-linecap="round" opacity=".35" transform="translate(-3 0)"/>
  <path d="M21 44 q 2 6 16 5 q 2 -4 -6 -6 l -5 -4 z" fill="#A8683A"/><path d="M19 49.5 h20" stroke="#E9B24A" stroke-width="2.2" stroke-linecap="round"/>
  <path d="M24 34 l 2 8 M22 43 l 12 3" fill="none" stroke="#E9B24A" stroke-width="1.6" stroke-linecap="round"/>
  <!-- torso -->
  <path d="M-9 -6 C -13 -28, -8 -48, 1 -58 L 15 -57 C 20 -44, 17 -24, 11 -6 Z" fill="url(#h-skin)"/>
  <path d="M-9 -6 C -13 -28, -8 -48, 1 -58 C -3 -44, -4 -24, -2 -6 Z" fill="#7E4A28" opacity=".45"/>
  <path d="M8 -44 q 6 3 9 -1 M9 -30 q 3 2 6 0" fill="none" stroke="#7E4A28" stroke-width="1.3" stroke-linecap="round" opacity=".6"/>
  <!-- shendyt kilt and belt -->
  <path d="M-11 -9 L 12 -12 L 32 2 Q 30 14 22 17 L -8 11 Q -13 2 -11 -9 Z" fill="#F6F0E0"/>
  <path d="M-6 -2 L 20 12 M0 -8 L 27 7 M-9 4 L 8 13" fill="none" stroke="#CFC5AC" stroke-width="1.2"/>
  <path d="M-11 -9 L 12 -12" stroke="#E9B24A" stroke-width="5" stroke-linecap="round"/><path d="M4 -11 l 6 13 l -9 2 z" fill="#1E3A9A"/><path d="M4 -11 l 6 13" stroke="#E9B24A" stroke-width="1.4"/>
  <!-- neck and head in profile -->
  <path d="M6 -58 L 8 -69" stroke="url(#h-skin)" stroke-width="8.5" stroke-linecap="round"/>
  <path d="M-1 -88 C 2 -98, 18 -98, 21.5 -86 L 20 -80 L 6 -72 L -2 -57 L -12 -55 C -10 -68, -7 -80, -1 -88 Z" fill="url(#h-nemes)"/>
  <path d="M4 -68 C 2 -75, 2 -84, 8 -89 C 14 -92, 20 -89, 21 -84 L 22 -80.5 L 25.6 -75.4 L 22.6 -74.4 L 23.2 -72.6 L 22.2 -71.4 L 22.8 -69.4 C 21 -66.4, 16 -65.6, 11 -67 Z" fill="url(#h-skin)"/>
  <path d="M22.3 -72 l -2.6 .5" stroke="#6A3A20" stroke-width="1" stroke-linecap="round"/>
  <path d="M15.8 -80.2 q 2.6 -2 5.2 -.2 q -2.6 1.4 -5.2 .2 z" fill="#fff"/><circle cx="18.8" cy="-80.2" r="1.15" fill="#17122B"/>
  <path d="M10.5 -79.2 L 15.8 -80.2 q 2.6 -2.2 5.4 -.2" fill="none" stroke="#17122B" stroke-width="1.2" stroke-linecap="round"/>
  <path d="M14.5 -83.6 q 3.6 -1.8 6.6 -.6" fill="none" stroke="#17122B" stroke-width="1.4" stroke-linecap="round"/>
  <path d="M20.5 -67 l 2.2 9.5 l -3.6 .6 l -1.2 -9.4 z" fill="#1E3A9A"/><path d="M19 -64 h3 M19.6 -61 h3" stroke="#E9B24A" stroke-width=".9"/>
  <!-- nemes: brow band, the lappet on the chest, the cobra -->
  <path d="M5 -80 L 12 -82 L 18 -49 L 9 -47 Z" fill="url(#h-nemes)"/>
  <path d="M21.5 -86 Q 12 -84 4 -79" fill="none" stroke="#E9B24A" stroke-width="2.6" stroke-linecap="round"/>
  <path d="M21 -87 q 6 -1 5 -8 q -4 1 -3.4 5" fill="none" stroke="#F7BE55" stroke-width="2.2" stroke-linecap="round"/>
  <!-- broad collar -->
  <path d="M-3 -57 Q 7 -45 17 -55" fill="none" stroke="#1E3A9A" stroke-width="7" stroke-linecap="round"/>
  <path d="M-2 -59 Q 7 -49 16 -57" fill="none" stroke="#E9B24A" stroke-width="2.4" stroke-linecap="round"/><path d="M-4 -54 Q 7 -41 18 -52" fill="none" stroke="#61D8CB" stroke-width="2" stroke-linecap="round" stroke-dasharray="2 2.4"/>
  <!-- near arm, holding the reins -->
  <path d="M9 -53 L 22 -36" fill="none" stroke="url(#h-skin)" stroke-width="9" stroke-linecap="round"/>
  <path d="M22 -36 L 40 -42" fill="none" stroke="url(#h-skin)" stroke-width="7.5" stroke-linecap="round"/>
  <path d="M12 -47 l 7 -5" stroke="#E9B24A" stroke-width="3.2" stroke-linecap="round"/><path d="M34 -43.5 l 1.6 5" stroke="#E9B24A" stroke-width="3" stroke-linecap="round"/>
  <circle cx="41" cy="-42.4" r="4.4" fill="#B5713F"/>'''


def _elephant() -> str:
    """The PHP mascot: a round blue elephant with php written on its side. Feet on y=0, middle at x=0, heading right."""
    def leg(x, cls, fill, toe):
        return (f'<g class="h-leg {cls}"><path d="M{x - 24} -96 h48 v82 a14 14 0 0 1 -14 14 h-20 a14 14 0 0 1 -14 -14 z" fill="{fill}" stroke="{OUT}" stroke-width="3"/>'
                f'<path d="M{x - 4} -1 a5.5 5.5 0 0 1 11 0 M{x + 9} -3 a5 5 0 0 1 10 0 M{x - 17} -1 a5.5 5.5 0 0 1 11 0" fill="{toe}" stroke="{OUT}" stroke-width="1.6"/></g>')
    trunk = "M138 -150 C 178 -150, 194 -112, 186 -76 C 181 -54, 198 -44, 214 -58"
    return f'''
<ellipse class="h-shadow" cx="20" cy="6" rx="170" ry="11" fill="#6B2E12"/>
<g class="h-ele">
 {leg(-52, "b", "#6A74A8", "#B9C0E2")}{leg(100, "d", "#6A74A8", "#B9C0E2")}
 <g class="h-tail"><path d="M-150 -96 C -146 -128, -138 -150, -124 -164" fill="none" stroke="{OUT}" stroke-width="9" stroke-linecap="round"/><path d="M-150 -96 C -146 -128, -138 -150, -124 -164" fill="none" stroke="#8892BF" stroke-width="5" stroke-linecap="round"/><path d="M-158 -82 q 8 -18 14 -2 q -6 10 -14 2 z" fill="{OUT}"/></g>
 <g class="h-trunk"><path d="{trunk}" fill="none" stroke="{OUT}" stroke-width="36" stroke-linecap="round"/></g>
 <path d="M-128 -70 C -146 -122, -138 -182, -96 -198 C -40 -216, 40 -216, 84 -206 C 126 -218, 164 -192, 164 -150 C 164 -122, 142 -102, 120 -96 C 112 -70, 100 -58, 80 -56 L -100 -56 C -116 -56, -124 -62, -128 -70 Z" fill="url(#h-body)" stroke="{OUT}" stroke-width="3"/>
 <path d="M-112 -74 C -70 -58, 40 -58, 96 -72 C 84 -58, 70 -58, 60 -58 L -98 -58 Z" fill="#5A649C" opacity=".35"/>
 <path d="M-104 -186 C -50 -206, 30 -206, 78 -198" fill="none" stroke="#C5CBEA" stroke-width="5" stroke-linecap="round" opacity=".5"/>
 {leg(-84, "a", "url(#h-body)", "#E4E8FA")}{leg(60, "c", "url(#h-body)", "#E4E8FA")}
 <text x="-36" y="-106" text-anchor="middle" font-family="Sora, 'Arial Black', Arial, sans-serif" font-style="italic" font-weight="800" font-size="58" letter-spacing="-2.5" fill="#262B57">php</text>
 <!-- the rug under the rider -->
 <path d="M-26 -212 Q 14 -220 54 -209 L 57 -170 Q 16 -161 -28 -171 Z" fill="url(#h-cloth)" stroke="#9A4A1C" stroke-width="1.5"/>
 <path d="M-27 -196 Q 14 -204 56 -194 M-28 -182 Q 15 -173 57 -181" fill="none" stroke="#1E3A9A" stroke-width="3.2"/>
 <path d="M-28 -168 Q 16 -158 57 -167" fill="none" stroke="#61D8CB" stroke-width="5" stroke-dasharray="2.5 5" stroke-linecap="round"/>
 <!-- head: trunk, ear, eye -->
 <g class="h-trunk"><path d="{trunk}" fill="none" stroke="url(#h-head)" stroke-width="30" stroke-linecap="round"/>
  <path d="M176 -92 q 8 -3 14 2 M175 -78 q 8 -2 13 3 M180 -64 q 7 -3 12 3" fill="none" stroke="{OUT}" stroke-width="1.8" stroke-linecap="round" opacity=".5"/></g>
 <path d="M118 -106 q 12 9 26 0" fill="none" stroke="{OUT}" stroke-width="2.4" stroke-linecap="round"/>
 <g class="h-ear"><path d="M98 -200 C 50 -214, 22 -176, 36 -130 C 46 -98, 88 -92, 102 -120 C 112 -146, 110 -178, 98 -200 Z" fill="#7B85B6" stroke="{OUT}" stroke-width="3"/><path d="M88 -180 C 62 -186, 48 -162, 54 -136 C 60 -116, 80 -114, 90 -128" fill="none" stroke="{OUT}" stroke-width="2" opacity=".45"/></g>
 <ellipse cx="134" cy="-162" rx="5.5" ry="7" fill="#12102A"/><circle cx="135.6" cy="-165" r="2" fill="#fff"/>
 <path d="M122 -178 q 12 -9 24 -2" fill="none" stroke="{OUT}" stroke-width="3" stroke-linecap="round"/>
 <!-- brow band and reins -->
 <path d="M96 -205 Q 124 -214 150 -196" fill="none" stroke="#E9B24A" stroke-width="5" stroke-linecap="round"/><circle cx="124" cy="-209" r="5" fill="#61D8CB" class="h-glow"/>
 <path d="M67 -255 Q 84 -226 100 -206" fill="none" stroke="#E9B24A" stroke-width="1.8" opacity=".9"/>
 <g transform="translate(20 -207) scale(1.15)"><g class="h-rider">{_rider()}</g></g>
</g>'''


def scene() -> str:
    rnd = random.Random(11)
    base = 318
    sx, sy = 590, 236
    rays = "".join(
        f'<polygon points="{sx},{sy} {sx + 420 * math.cos(a - .05):.0f},{sy + 420 * math.sin(a - .05):.0f} {sx + 420 * math.cos(a + .05):.0f},{sy + 420 * math.sin(a + .05):.0f}" fill="#fff" opacity=".11"/>'
        for a in (i * math.tau / 14 for i in range(14)))
    clouds = (_cloud(120, -250, 1.5, .75) + _cloud(520, -310, 1.1, .7) + _cloud(930, -210, 1.7, .8) + _cloud(760, -20, 1.25, .75) + _cloud(1090, 70, .9, .65) + _cloud(300, 110, 1.0, .6))
    birds = _birds(820, -130, 3, rnd) + _birds(1040, 120, 3, rnd) + _birds(300, 150, 2, rnd)
    far = _skyline(rnd, base)
    nile = f'<rect x="0" y="{base - 3}" width="{W}" height="24" fill="#35BDB1"/>'
    glints = "".join(f'<rect class="h-glint" style="animation-delay:-{rnd.uniform(0, 1.8):.1f}s" x="{rnd.randint(0, W - 30)}" y="{base + rnd.choice([1, 5, 9])}" width="{rnd.randint(10, 28)}" height="1.6" rx=".8" fill="#fff" opacity=".8"/>' for _ in range(22))
    pyramids = _pyr(250, 196, 150, base + 6) + _pyr(456, 236, 100, base + 6) + _pyr(600, 268, 62, base + 6) + _pyr(1040, 244, 92, base + 6, .2)
    dunes = (f'<path d="M0 {base + 12} C 150 {base - 10}, 300 {base + 24}, 470 {base + 8} S 780 {base - 12}, 940 {base + 10} S 1120 {base + 22}, 1200 {base + 12} L 1200 420 L 0 420 Z" fill="url(#h-dune)"/>')
    near = (_palm(130, 352, 104) + _palm(170, 354, 76, -1) + _palm(760, 352, 92, -1)
            + '<path d="M430 354 l7 -90 l4 -8 l4 8 l7 90 z" fill="#E9A24E"/><path d="M441 256 l4 8 l7 90 l-11 0 z" fill="#C97A36"/>'
            + '<path d="M940 354 q 30 -26 62 -4 q 22 -14 44 4 z" fill="#E8A557"/>'
            + '<path d="M556 354 q 6 -18 12 -2 q 4 -22 10 -1 q 6 -14 10 3 z M 296 354 q 5 -14 10 -1 q 5 -16 9 1 z M1124 354 q 6 -16 11 -1 q 5 -18 10 1 z" fill="#2A9A72"/>')
    ground_marks = "".join(
        f'<rect x="{rnd.randint(0, W - 60)}" y="{rnd.randint(GROUND - 8, 414)}" width="{rnd.randint(18, 70)}" height="{rnd.choice([1.5, 2, 3])}" rx="1.5" fill="{rnd.choice(["#FFE3A8", "#B8682C"])}" opacity="{rnd.uniform(.35, .7):.2f}"/>'
        for _ in range(30)) + "".join(
        f'<ellipse cx="{rnd.randint(0, W)}" cy="{rnd.randint(GROUND, 414)}" rx="{rnd.randint(4, 9)}" ry="2.5" fill="#A85A2B" opacity=".55"/>' for _ in range(14))
    front = "".join(
        f'<path d="M{x} 424 q {w * .3} {-h} {w * .55} {-h * .2} q {w * .2} {-h * .5} {w * .45} {h * .2} z" fill="#9A4F27"/>'
        for x, w, h in ((40, 150, 34), (420, 110, 24), (700, 190, 40), (1010, 120, 28)))
    streaks = "".join(
        f'<rect class="h-streak" x="0" y="{y}" width="{w}" height="{t}" rx="1" fill="{c}" opacity="{o}" style="animation-duration:{d}s;animation-delay:-{rnd.uniform(0, d):.2f}s"/>'
        for y, w, t, c, o, d in (
            (136, 160, 2, "#fff", .8, 1.3), (182, 240, 1.5, "#fff", .7, .9), (218, 120, 2.5, "#fff", .6, 1.1),
            (256, 300, 1.5, INK, .25, .8), (290, 140, 2, "#fff", .75, 1.4), (158, 90, 1.5, INK, .2, 1),
            (334, 220, 2, "#fff", .7, .7), (366, 260, 2.5, "#fff", .55, .6), (108, 200, 1.5, "#fff", .6, 1.6)))
    ex, ey = 0, 0  # the elephant's group is placed and scaled as one
    trails = "".join(
        f'<path class="h-trail" style="animation-duration:{d}s" d="M{ex - 96} {ey - y0} C {ex - 260} {ey - y0 - a}, {ex - 420} {ey - y0 + a}, {ex - 600} {ey - y0 - a * .4} S {ex - 880} {ey - y0 + a}, {ex - 1100} {ey - y0}" fill="none" stroke="url(#{g})" stroke-width="{sw}" stroke-linecap="round"/>'
        for y0, a, g, sw, d in ((150, 22, "h-tr1", 5, .7), (118, 16, "h-tr2", 3.5, .55), (88, 26, "h-tr1", 4, .85), (182, 12, "h-tr3", 2.5, .6)))
    dust = "".join(
        f'<circle class="h-dust" cx="{ex + dx}" cy="{ey - 6 + dy}" r="{r}" fill="#FFEFD0" stroke="#E0914A" stroke-width=".8" filter="url(#h-soft)" style="animation-delay:-{d}s"/>'
        for dx, dy, r, d in ((-70, 0, 15, 0), (-40, 2, 12, .22), (80, 0, 13, .44), (50, 3, 10, .66), (-90, -2, 17, .88), (-20, 1, 11, .33), (100, 2, 10, .77)))
    sparks = "".join(
        f'<circle class="h-spark" cx="{ex + dx}" cy="{ey - dy}" r="{r}" fill="{c}" style="--dy:{vy}px;animation-duration:{d}s;animation-delay:-{rnd.uniform(0, d):.2f}s"/>'
        for dx, dy, r, c, vy, d in (
            (-90, 130, 3.2, "#fff", -30, .9), (-100, 100, 2.6, "#12B3A6", 10, .7), (-80, 160, 2.4, "#FFC043", -50, 1.1),
            (-110, 70, 2.8, "#fff", 24, .8), (-70, 190, 2.2, "#4F57C4", -60, 1), (-96, 46, 2.4, "#fff", 14, .6),
            (-60, 226, 2.6, "#FFC043", -40, 1.2), (-104, 118, 2, "#fff", -10, .5)))
    return f'''<svg viewBox="0 -380 {W} {H + 380}" preserveAspectRatio="xMidYMax slice" role="img" aria-labelledby="h-title">
<title id="h-title">A pharaoh rides the PHP elephant at full gallop past the pyramids of Giza and Cairo Tower at sunset.</title>
<style>{CSS}</style>
<defs>{DEFS}</defs>
<rect x="0" y="-380" width="{W}" height="{380 + base + 30}" fill="url(#h-sky)"/>
<g class="h-sun"><circle class="h-sunpulse" cx="{sx}" cy="{sy}" r="230" fill="url(#h-halo)"/><g class="h-rays">{rays}</g><circle cx="{sx}" cy="{sy}" r="60" fill="url(#h-sunfill)"/></g>
{_layer("h-l0", clouds)}
{_layer("h-l1", birds)}
{_layer("h-l1", far)}
{nile}<g>{glints}</g>
{_layer("h-l2", pyramids)}
{_layer("h-l2", dunes)}
<path d="M0 {base + 32} L {W} {base + 32} L {W} {H} L 0 {H} Z" fill="url(#h-sand)"/>
{_layer("h-l3", near)}
{_layer("h-l4", ground_marks)}
<g>{streaks}</g>
<g class="h-hero" transform="translate(850 {GROUND}) scale(1.04)">{trails}{sparks}{_elephant()}{dust}</g>
{_layer("h-l5", front)}
</svg>'''

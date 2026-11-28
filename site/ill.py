"""Illustrations: code on the left, an animated picture of what Cairo does on the right.

A scene is data (scenes_*.py): lanes (Go, a PHP thread, the waits of a thread, ...),
tokens that move between them (requests, fibers, jobs), and steps. Each step says
which code lines it is about, what to read under the picture, and where tokens are.
build.py puts a scene where a Markdown page has `<!-- illustration: id -->`, and
src/ill.js plays the steps. Without JavaScript the first step and the steps as text show.
"""
import html
import json
import re
from dataclasses import dataclass, field

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PhpLexer, get_lexer_by_name

W = 440                 # the picture's width in SVG units
PAD, LANE_H, GAP = 12, 58, 10
SLOT_X0, SLOT_DX = 58, 80  # centre of slot 0, distance between slots (0 to 4 fit)
TOK_W, TOK_H, SMALL_W, SMALL_H = 70, 28, 52, 22
HUES = ["#FFC043", "#5FD9CC", "#B6C1FF", "#FF9F8A", "#A8E07A", "#FFA9BC", "#C9CEF1"]
DEFAULT_STATE = {"go": "queued", "queue": "queued", "php": "run", "wait": "wait", "off": "run"}
STATES = {"queued", "run", "wait", "done", "fail", "hidden"}


@dataclass
class Lane:
    id: str
    label: str
    kind: str = "php"   # go, php, wait, off, queue
    sub: str = ""


@dataclass
class Tok:
    id: str
    label: str
    hue: int = 0
    small: bool = False


@dataclass
class Mark:
    id: str
    text: str
    lane: str
    slot: float
    tone: str = "gold"  # gold, nile, sun, red, muted


@dataclass
class Step:
    say: str
    lines: tuple = ()     # code lines: a number (from 1) or text the line contains
    clock: str = ""
    at: dict = field(default_factory=dict)  # token id: (lane, slot[, state]); lane "-" hides it
    show: tuple = ()      # marks to show in this step only
    lit: tuple = ()       # lanes to light in this step only


@dataclass
class Scene:
    id: str
    title: str
    code: list            # [(file name, language, source)]
    lanes: list
    tokens: list
    steps: list
    marks: list = field(default_factory=list)


FMT = HtmlFormatter(nowrap=True)


def _code_lines(lang: str, src: str) -> list:
    lexer = PhpLexer(startinline=not src.startswith("<?php")) if lang == "php" else get_lexer_by_name(lang)
    return highlight(src.rstrip("\n") + "\n", lexer, FMT).rstrip("\n").split("\n")


def _line_index(scene: Scene) -> list:
    """Every code line as (file index, plain text), in order."""
    out = []
    for fi, (_, _, src) in enumerate(scene.code):
        out += [(fi, line) for line in src.rstrip("\n").split("\n")]
    return out


def _resolve_lines(scene: Scene, refs) -> list:
    plain = _line_index(scene)
    found = []
    for ref in refs:
        if isinstance(ref, int):
            if not 1 <= ref <= len(plain):
                raise SystemExit(f"illustration {scene.id}: no line {ref}")
            found.append(ref - 1)
            continue
        hits = [i for i, (_, text) in enumerate(plain) if ref in text]
        if not hits:
            raise SystemExit(f"illustration {scene.id}: no line contains {ref!r}")
        found.append(hits[0])
    return found


def _lane_y(scene: Scene) -> dict:
    return {lane.id: PAD + i * (LANE_H + GAP) for i, lane in enumerate(scene.lanes)}


def _pos(scene: Scene, lanes_y: dict, lane: str, slot: float) -> tuple:
    if lane not in lanes_y:
        raise SystemExit(f"illustration {scene.id}: no lane {lane!r}")
    return round(SLOT_X0 + slot * SLOT_DX, 1), lanes_y[lane] + 38


def _states(scene: Scene) -> list:
    """The full place and state of every token at every step: [{id: [x, y, state]}]."""
    lanes_y = _lane_y(scene)
    kinds = {lane.id: lane.kind for lane in scene.lanes}
    ids = {t.id for t in scene.tokens}
    cur = {}
    out = []
    for n, step in enumerate(scene.steps):
        for tid, where in step.at.items():
            if tid not in ids:
                raise SystemExit(f"illustration {scene.id}: step {n + 1} moves unknown token {tid!r}")
            if where[0] == "-":
                x, y, _ = cur.get(tid, (0, 0, ""))
                cur[tid] = (x + 24, y, "hidden")
                continue
            lane, slot = where[0], where[1]
            state = where[2] if len(where) > 2 else DEFAULT_STATE[kinds.get(lane, "php")]
            if state not in STATES:
                raise SystemExit(f"illustration {scene.id}: unknown state {state!r}")
            x, y = _pos(scene, lanes_y, lane, slot)
            cur[tid] = (x, y, state)
        out.append({k: list(v) for k, v in cur.items()})
    # a token comes in from the left of the place it first appears at
    for t in scene.tokens:
        first = next((s[t.id] for s in out if t.id in s and s[t.id][2] != "hidden"), None)
        if first is None:
            raise SystemExit(f"illustration {scene.id}: token {t.id!r} never shows")
        for s in out:
            if t.id in s and s[t.id][2] != "hidden":
                break
            s[t.id] = [first[0] - 24, first[1], "hidden"]
    return out


def _inline(text: str) -> str:
    """Escapes a caption and turns `code` into <code>."""
    parts = text.split("`")
    return "".join(f"<code>{html.escape(p)}</code>" if i % 2 else html.escape(p) for i, p in enumerate(parts))


def _token_svg(t: Tok, x: float, y: float, state: str) -> str:
    # wide enough for the label (a big token keeps room for its state icon)
    w = max(SMALL_W, round(len(t.label) * 6.4 + 14)) if t.small else max(TOK_W, round(len(t.label) * 7.4 + 30))
    h = SMALL_H if t.small else TOK_H
    icons = "" if t.small else (
        '<g class="ic i-run"><path d="M-27 -4.5 L-20 0 L-27 4.5 Z"/></g>'
        '<g class="ic i-wait"><circle cx="-23" cy="0" r="5"/><path d="M-23 -2.6 V0 L-21.2 1.4"/></g>'
        '<g class="ic i-done"><path d="M-27 0 L-24 3 L-19 -3"/></g>'
        '<g class="ic i-fail"><path d="M-26.5 -3.5 L-19.5 3.5 M-19.5 -3.5 L-26.5 3.5"/></g>'
        '<g class="ic i-queued"><circle cx="-23" cy="0" r="2.4"/></g>')
    tx = 0 if t.small else 6
    return (f'<g class="tok s-{state}{" small" if t.small else ""}" data-t="{t.id}" '
            f'style="--h:{HUES[t.hue % len(HUES)]};transform:translate({x}px,{y}px)">'
            f'<rect class="halo" x="{-w / 2}" y="{-h / 2}" width="{w}" height="{h}" rx="{h / 2 - 3}"/>'
            f'<rect class="body" x="{-w / 2}" y="{-h / 2}" width="{w}" height="{h}" rx="{h / 2 - 3}"/>'
            f'{icons}<text x="{tx}" y="0.5">{html.escape(t.label)}</text></g>')


def _mark_svg(scene: Scene, lanes_y: dict, m: Mark, on: bool) -> str:
    x, y = _pos(scene, lanes_y, m.lane, m.slot)
    w = round(len(m.text) * 6.1 + 18)
    return (f'<g class="mark t-{m.tone}{" on" if on else ""}" data-m="{m.id}" transform="translate({x},{y})">'
            f'<rect x="{-w / 2}" y="-11" width="{w}" height="22" rx="11"/><text y="0.5">{html.escape(m.text)}</text></g>')


def _svg(scene: Scene, first: dict) -> str:
    lanes_y = _lane_y(scene)
    height = PAD * 2 + len(scene.lanes) * (LANE_H + GAP) - GAP
    lanes = []
    for lane in scene.lanes:
        y = lanes_y[lane.id]
        lit = " lit" if lane.id in scene.steps[0].lit else ""
        sub = (f'<text class="sub" x="{W - PAD - 12}" y="{y + 16}">{html.escape(lane.sub)}</text>' if lane.sub else "")
        lanes.append(f'<g class="lane k-{lane.kind}{lit}" data-l="{lane.id}">'
                     f'<rect x="{PAD}" y="{y}" width="{W - 2 * PAD}" height="{LANE_H}" rx="12"/>'
                     f'<text class="lbl" x="{PAD + 12}" y="{y + 16}">{html.escape(lane.label)}</text>{sub}</g>')
    marks = "".join(_mark_svg(scene, lanes_y, m, m.id in scene.steps[0].show) for m in scene.marks)
    toks = "".join(_token_svg(t, *first[t.id]) for t in scene.tokens)
    return (f'<svg class="ill-svg" viewBox="0 0 {W} {height}" role="img" aria-label="{html.escape(scene.title)}">'
            f'{"".join(lanes)}{marks}{toks}</svg>')


ICON_PLAY = '<svg class="i-play" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>'
ICON_PAUSE = '<svg class="i-pause" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z"/></svg>'
ICON_PREV = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5 8 12l7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ICON_NEXT = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def render(scene: Scene) -> str:
    states = _states(scene)
    marks = {m.id for m in scene.marks}
    lanes = {lane.id for lane in scene.lanes}
    steps = []
    for n, step in enumerate(scene.steps):
        for ref in step.show:
            if ref not in marks:
                raise SystemExit(f"illustration {scene.id}: step {n + 1} shows unknown mark {ref!r}")
        for ref in step.lit:
            if ref not in lanes:
                raise SystemExit(f"illustration {scene.id}: step {n + 1} lights unknown lane {ref!r}")
        steps.append({"t": states[n], "m": list(step.show), "l": list(step.lit),
                      "c": _resolve_lines(scene, step.lines), "k": step.clock})

    on = set(steps[0]["c"])
    files, i = [], 0
    for name, lang, src in scene.code:
        rows = []
        for line in _code_lines(lang, src):
            rows.append(f'<span class="ln{" on" if i in on else ""}" data-i="{i}">{line or " "}</span>')
            i += 1
        files.append(f'<div class="ill-file"><p class="ill-fname">{html.escape(name)}</p>'
                     f'<pre class="hl"><code>{"".join(rows)}</code></pre></div>')

    says = "".join(f"<li>{_inline(s.say)}</li>" for s in scene.steps)
    dots = "".join(f'<button type="button" class="dot{" on" if n == 0 else ""}" aria-label="Step {n + 1}"></button>'
                   for n in range(len(scene.steps)))
    data = json.dumps(steps, separators=(",", ":")).replace("</", "<\\/")
    return f'''<figure class="ill" id="ill-{scene.id}">
<figcaption class="ill-head"><span class="ill-kicker">See it run</span><b>{html.escape(scene.title)}</b></figcaption>
<div class="ill-body">
<div class="ill-code{" focus" if on else ""}">{"".join(files)}</div>
<div class="ill-stage">{_svg(scene, states[0])}<span class="ill-clock"{"" if steps[0]["k"] else " hidden"}>{html.escape(steps[0]["k"])}</span>
<ul class="ill-legend" aria-hidden="true"><li class="lg-run">runs</li><li class="lg-wait">waits, thread free</li><li class="lg-queued">queued</li><li class="lg-done">answered</li></ul></div>
</div>
<div class="ill-bar">
<div class="ill-btns"><button type="button" class="ill-prev" aria-label="Previous step">{ICON_PREV}</button><button type="button" class="ill-play" aria-label="Play">{ICON_PLAY}{ICON_PAUSE}</button><button type="button" class="ill-next" aria-label="Next step">{ICON_NEXT}</button></div>
<p class="ill-say"><span class="ill-n">1/{len(steps)}</span> {_inline(scene.steps[0].say)}</p>
<div class="ill-dots">{dots}</div>
<span class="ill-prog"><i></i></span>
</div>
<details class="ill-text"><summary>The steps as text</summary><ol>{says}</ol></details>
<script type="application/json" class="ill-data">{data}</script>
</figure>'''


MARKER = re.compile(r"<!--\s*illustration:\s*([a-z0-9-]+)\s*-->")


def expand(body: str, scenes: dict, page: str) -> str:
    """Replaces each `<!-- illustration: id -->` of a rendered page with its scene."""
    def one(m):
        if m.group(1) not in scenes:
            raise SystemExit(f"{page}.md names an unknown illustration {m.group(1)!r}")
        return render(scenes[m.group(1)])
    return MARKER.sub(one, body)

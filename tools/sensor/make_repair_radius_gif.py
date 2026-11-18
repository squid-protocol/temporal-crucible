#!/usr/bin/env python3
"""Animated explainer of the repair radius: four functions, "if this happens, this tends to follow". Numbers from docs/sensor-overhaul/sensors/ripple_radius.md.

    python tools/sensor/make_repair_radius_gif.py OUT.gif [--frames-dir DIR]"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1000, 660
BG, INK, MUTED = "#fbfaf6", "#1f2937", "#6b7280"
BOX, BOX_LINE = "#ebe8df", "#6b7280"
ORANGE, RED, AMBER, BLUE, GREEN = "#f59e0b", "#dc2626", "#fbbf24", "#2563eb", "#059669"
FD = "/usr/share/fonts/truetype/dejavu/"
F = lambda sz, bold=False: ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), sz)  # noqa: E731
M = lambda sz: ImageFont.truetype(FD + "DejaVuSansMono.ttf", sz)  # noqa: E731
POS = {"A": (90, 150, 290, 240), "B": (400, 150, 600, 240), "C": (710, 150, 910, 240), "D": (400, 335, 600, 425)}
NAME = {"A": "A", "B": "B", "C": "C", "D": "D"}


def wrap(d, text, font, width):
    out, line = [], ""
    for w in text.split():
        t = (line + " " + w).strip()
        if d.textlength(t, font=font) <= width:
            line = t
        else:
            out.append(line)
            line = w
    return out + [line]


def arrow(d, p, q, color=MUTED, w=4):
    d.line([p, q], fill=color, width=w)
    dx = 1 if q[0] > p[0] else -1
    d.polygon([q, (q[0] - 16 * dx, q[1] - 9), (q[0] - 16 * dx, q[1] + 9)], fill=color)


def dotted(d, p, q, color=MUTED, w=3):
    n = int(((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** 0.5 // 14)
    for i in range(n):
        if i % 2 == 0:
            a, b = i / n, (i + 1) / n
            d.line([(p[0] + (q[0] - p[0]) * a, p[1] + (q[1] - p[1]) * a), (p[0] + (q[0] - p[0]) * b, p[1] + (q[1] - p[1]) * b)], fill=color, width=w)


def graph(d, fills=None, notes=None, ring=None, link=True, snippet=None):
    fills, notes = fills or {}, notes or {}
    for k in ring or []:
        x0, y0, x1, y1 = POS[k]
        d.rounded_rectangle((x0 - 12, y0 - 12, x1 + 12, y1 + 12), 22, outline=AMBER, width=6)
    arrow(d, (292, 195), (398, 195))
    arrow(d, (602, 195), (708, 195))
    d.text((345, 160), "calls", font=F(15), fill=MUTED, anchor="mm")
    d.text((655, 160), "calls", font=F(15), fill=MUTED, anchor="mm")
    if link:
        dotted(d, (500, 244), (500, 333))
        d.text((515, 288), "both use the setting  timeout", font=F(15), fill=MUTED, anchor="lm")
    for k, (x0, y0, x1, y1) in POS.items():
        fill = fills.get(k, BOX)
        d.rounded_rectangle((x0, y0, x1, y1), 16, fill=fill, outline=BOX_LINE if k not in fills else INK, width=3)
        d.text(((x0 + x1) / 2, (y0 + y1) / 2 - (10 if k in notes else 0)), NAME[k], font=F(40, True), fill=INK if fill in (BOX, AMBER, ORANGE) else "white", anchor="mm")
        if k in notes:
            d.text(((x0 + x1) / 2, (y0 + y1) / 2 + 26), notes[k], font=F(15, True), fill=INK if fill in (BOX, AMBER, ORANGE) else "white", anchor="mm")
    d.text((500, 445), "(in another file)", font=F(14), fill=MUTED, anchor="mm")
    if snippet:
        x0, y0, x1, y1 = POS["A"]
        d.rounded_rectangle((x0 - 40, y1 + 40, x1 + 70, y1 + 130), 10, fill="#f3f4f6", outline=BOX_LINE, width=2)
        for i, ln in enumerate(snippet):
            d.text((x0 - 28, y1 + 52 + i * 26), ln, font=M(17), fill=INK)


def caption(d, pairs, top=470, left=40, width=920):
    y = top
    for kind, text in pairs:
        if kind == "plain":
            for ln in wrap(d, text, F(23), width):
                d.text((left, y), ln, font=F(23), fill=INK)
                y += 33
            continue
        lab, col = ("IF", BLUE) if kind == "if" else ("THEN", GREEN)
        d.rounded_rectangle((left, y + 2, left + 74, y + 34), 8, fill=col)
        d.text((left + 37, y + 18), lab, font=F(18, True), fill="white", anchor="mm")
        lines = wrap(d, text, F(23, kind == "if"), width - 100)
        for ln in lines:
            d.text((left + 92, y), ln, font=F(23, kind == "if"), fill=INK)
            y += 33
        y += 8


def frame(title, draw_fn):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((40, 28), title, font=F(22, True), fill=INK)
    draw_fn(d)
    return im


def mini(d, ox, oy, scatter):
    d.rounded_rectangle((ox, oy, ox + 380, oy + 250), 14, outline=BOX_LINE, width=2)
    cx, cy = ox + 190, oy + 125
    pts = [(-120, -70), (130, -60), (-100, 80), (60, 90), (-30, -95), (150, 40), (-150, 10), (100, 100), (20, 40), (-60, 20)]
    for i, (dx, dy) in enumerate(pts):
        d.ellipse((cx + dx - 11, cy + dy - 11, cx + dx + 11, cy + dy + 11), fill="#d1d5db", outline=BOX_LINE)
    d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=ORANGE, outline=INK, width=3)
    d.text((cx, cy), "B", font=F(22, True), fill=INK, anchor="mm")
    if scatter:
        for dx, dy in [(-120, -70), (130, -60), (-100, 80), (60, 90), (150, 40), (-30, -95)]:
            d.ellipse((cx + dx - 11, cy + dy - 11, cx + dx + 11, cy + dy + 11), fill=RED, outline=INK, width=2)
    else:
        d.ellipse((cx + 20 - 11, cy + 40 - 11, cx + 20 + 11, cy + 40 + 11), fill=RED, outline=INK, width=2)
        d.ellipse((cx - 36, cy - 36, cx + 36, cy + 36), outline=AMBER, width=5)


FRAMES = []
FRAMES.append((4.0, frame("What tends to happen after a function is changed?", lambda d: (graph(d), caption(d, [("plain", "Four functions. A calls B. B calls C. D is in another file but uses the same setting, timeout.")])))))
FRAMES.append((4.5, frame("Day 1", lambda d: (graph(d, {"B": ORANGE}, {"B": "changed"}), caption(d, [("plain", "A developer changes B. Say B now returns an error code when the setting is missing. It used to return zero.")])))))
FRAMES.append((5.5, frame("Weeks or months later", lambda d: (graph(d, {"B": RED}, {"B": "bug found"}), caption(d, [("if", "a bug caused by the change turns up"), ("then", "the fix is most often in B itself: 43% to 72% of the time, depending on the project.")])))))
FRAMES.append((6.0, frame("Not in B? Then probably next door", lambda d: (graph(d, {"B": RED}, {"B": "bug found"}, ring=["A", "C"]), caption(d, [("if", "the fix is not in B"), ("then", "it is more often in a close neighbour (A or C) than in a random function of the same size in the same file: 1.6 to 2.2 times as often.")])))))
FRAMES.append((7.0, frame("If it is A, the callers", lambda d: (graph(d, {"A": AMBER, "B": RED}, {"A": "fix here", "B": "bug found"}, snippet=["if (B() < 0) {", "    handle_error();", "}"]), caption(d, [("if", "the result or arguments of B changed"), ("then", "the callers (A) often need a new check on the result: 8 to 14 times as often as fixes inside B, and changed arguments about 1.6 times as often.")])))))
FRAMES.append((6.5, frame("If it is D, no call links needed", lambda d: (graph(d, {"D": AMBER, "B": RED}, {"D": "fix here", "B": "bug found"}), caption(d, [("if", "other code uses the same name as the change (timeout)"), ("then", "it can need a fix even though nothing calls anything: 45% of fixes with no call link still share a name with the original change.")])))))


def size_frame(d):
    mini(d, 60, 90, False)
    mini(d, 560, 90, True)
    d.text((250, 355), "small change (under 20 lines)", font=F(18, True), fill=INK, anchor="mm")
    d.text((750, 355), "big change (500+ lines)", font=F(18, True), fill=INK, anchor="mm")
    caption(d, [("if", "small"), ("then", "fixes stay close, usually one fix.")], top=385, left=40, width=440)
    caption(d, [("if", "big"), ("then", "fixes scatter and keep coming: half to three in four need 2+ fixes, against about one in seven.")], top=385, left=520, width=440)


FRAMES.append((7.0, frame("Size matters most", size_frame)))
FRAMES.append((5.5, frame("What does not happen", lambda d: (graph(d, {"B": RED}, {"B": "bug found"}, ring=["A", "C"]), d.text((500, 120), "no wave spreading outward", font=F(24, True), fill=RED, anchor="mm"), caption(d, [("if", "time passes"), ("then", "later fixes are only a little farther away (the radius weakens 6% to 21% over two years). No wave spreading outward.")])))))


def closing(d):
    d.rounded_rectangle((30, 80, W - 30, H - 55), 20, fill="#111827")
    d.text((W / 2, 135), "This appears to be useful as a checklist", font=F(34, True), fill="white", anchor="mm")
    d.text((W / 2, 180), "when you change a function:", font=F(24), fill="#d1d5db", anchor="mm")
    items = ["Look inside the function itself first.", "Check that its callers handle the new result.", "Search for other code using the same names.", "A big change? Plan for repeated follow-up fixes."]
    for i, t in enumerate(items):
        d.ellipse((120, 235 + i * 62, 154, 269 + i * 62), fill=GREEN)
        d.text((137, 252 + i * 62), str(i + 1), font=F(20, True), fill="white", anchor="mm")
        d.text((175, 252 + i * 62), t, font=F(25), fill="white", anchor="lm")
    for i, ln in enumerate(wrap(d, "A reminder, not a prediction. Patterns across thousands of C-code fixes in Linux, Mesa, DPDK, FreeBSD, OpenSSL and curl. Associations, not proof of cause.", F(16), 860)):
        d.text((W / 2, 520 + i * 24), ln, font=F(16), fill="#9ca3af", anchor="mm")


FRAMES.append((9.0, frame("The repair radius", closing)))

SLOW = 1.5  # slide time multiplier (the first version ran at 1.0)
FADE_STEPS, FADE_MS = 3, 90


def progress(im, i, n):
    """Slide progress: a counter at the top right and a bar with one dot per step along the bottom."""
    im = im.copy()
    d = ImageDraw.Draw(im)
    d.text((W - 40, 30), f"repair radius  \u00b7  {i + 1} / {n}", font=F(16), fill=MUTED, anchor="ra")
    x0, x1, y = 40, W - 40, H - 22
    d.rounded_rectangle((x0, y - 3, x1, y + 3), 3, fill="#d1d5db")
    d.rounded_rectangle((x0, y - 3, x0 + (x1 - x0) * (i + 1) / n, y + 3), 3, fill=BLUE)
    for k in range(n):
        cx = x0 + (x1 - x0) * (k + 0.5) / n
        d.ellipse((cx - 6, y - 6, cx + 6, y + 6), fill=BLUE if k <= i else "#d1d5db", outline="#fbfaf6", width=2)
    return im


def build():
    n = len(FRAMES)
    slides = [progress(im, i, n) for i, (_, im) in enumerate(FRAMES)]
    seq, dur = [], []
    for i, im in enumerate(slides):
        seq.append(im)
        dur.append(int(FRAMES[i][0] * SLOW * 1000))
        if i + 1 < n:
            for k in range(1, FADE_STEPS + 1):
                seq.append(Image.blend(im, slides[i + 1], k / (FADE_STEPS + 1)))
                dur.append(FADE_MS)
    return slides, seq, dur


if __name__ == "__main__":
    out = Path(sys.argv[1])
    slides, seq, dur = build()
    pal = [im.convert("P", palette=Image.ADAPTIVE, colors=64) for im in seq]
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=dur, loop=0, optimize=True)
    if "--frames-dir" in sys.argv:
        d = Path(sys.argv[sys.argv.index("--frames-dir") + 1])
        d.mkdir(parents=True, exist_ok=True)
        for i, im in enumerate(slides):
            im.save(d / f"frame_{i}.png")
    print(out, out.stat().st_size // 1024, "KB,", len(slides), "slides,", len(seq), "frames,", round(sum(dur) / 1000), "s")

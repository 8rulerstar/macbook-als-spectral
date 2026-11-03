#!/usr/bin/env python3
# Draw the README figures from data/ as SVG. Standard library only.
#
# Usage:
#   python3 make_figures.py          # writes docs/channels.svg, docs/red_green.svg
#
# Same method as analyze.py: median of the second half of each step, then each
# channel's share of c0..c4 (no cover subtraction).

import csv, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = [("macOS 27.0.1", "data/macos27.0.1_mac16-8.csv"),
        ("macOS 27.2 run 1", "data/macos27.2_mac16-8.csv"),
        ("macOS 27.2 run 2", "data/macos27.2_mac16-8_run2.csv")]
OPACITY = ["0.3", "0.6", "1"]               # cleanest run (27.2 run 2) darkest
COLORS = [("blue", "#2f6fdb"), ("green", "#2e9e4f"), ("red", "#d23b3b")]
INK, MUTED, GRID, BG = "#1f2328", "#59636e", "#d8dee4", "#ffffff"

def step_medians(path):
    steps = {}
    with open(os.path.join(HERE, path), newline="") as f:
        for r in csv.DictReader(f):
            steps.setdefault(r["phase"].lower().split()[0], []).append(r)
    out = {}
    for k, rows in steps.items():
        half = rows[len(rows) // 2:]
        out[k] = [statistics.median(float(r[f"c{i}"]) for r in half) for i in range(5)]
    return out

def share(v):
    t = sum(v)
    return [x / t for x in v]

def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}" font-family="-apple-system, Helvetica, Arial, sans-serif">'
            f'<rect width="{w}" height="{h}" fill="{BG}"/>{body}</svg>\n')

def text(x, y, s, size=13, fill=INK, anchor="start", weight="normal"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{s}</text>')

def channels_figure(data):
    # One panel per screen color; in each, c0..c4 shares, one bar per run.
    W, H, top, base, ph = 760, 300, 56, 250, 170
    pw, gap = 220, 30
    body = text(20, 28, "Channel share under each phone-screen color (c0..c4)", 16, weight="bold")
    body += text(20, 46, "Peak moves c0 to c2 to c4. Bars, light to dark: 27.0.1, 27.2 run 1, 27.2 run 2 (cleanest). Phone OLED, one Mac16,8.", 12, MUTED)
    for p, (name, col) in enumerate(COLORS):
        x0 = 30 + p * (pw + gap)
        for frac in (0, 0.25, 0.5, 0.75):
            y = base - frac / 0.75 * ph
            body += f'<line x1="{x0}" y1="{y:.1f}" x2="{x0 + pw}" y2="{y:.1f}" stroke="{GRID}"/>'
            if p == 0:
                body += text(x0 - 6, y + 4, f"{frac:.2f}", 10, MUTED, "end")
        for i in range(5):
            for j, (_, run) in enumerate(data):
                v = share(run[name])[i]
                bw = 11
                x = x0 + 8 + i * 42 + j * (bw + 2)
                hgt = v / 0.75 * ph
                op = OPACITY[j]
                body += (f'<rect x="{x}" y="{base - hgt:.1f}" width="{bw}" height="{hgt:.1f}" '
                         f'fill="{col}" fill-opacity="{op}"/>')
            body += text(x0 + 12 + i * 42 + 17, base + 16, f"c{i}", 11, MUTED, "middle")
        body += text(x0 + pw / 2, base + 36, f"{name} screen", 13, INK, "middle", "bold")
    return svg(W, H, body)

def red_green_figure(data):
    # Red/green contrast of the c3 share (4 channels) vs the c4 share (5 channels).
    rows = []
    for label, run in data:
        r, g = run["red"], run["green"]
        c3 = (r[3] / sum(r[:4])) / (g[3] / sum(g[:4]))
        c4 = (r[4] / sum(r)) / (g[4] / sum(g))
        rows.append((label, c3, c4))
    W, H, x0, scale = 760, 310, 170, 60
    body = text(20, 28, "How much more a channel responds to red than to green", 16, weight="bold")
    body += text(20, 46, "Share under red / share under green. Grey: c3 share of c0..c3, a simple 4-channel metric.", 12, MUTED)
    body += text(20, 62, "Red: c4 share of c0..c4. Phone OLED screens, one Mac16,8. Dashed line: 1x (no contrast).", 12, MUTED)
    body += (f'<line x1="{x0 + scale}" y1="72" x2="{x0 + scale}" y2="{H - 12}" '
             f'stroke="{MUTED}" stroke-dasharray="3 3"/>')
    y = 82
    for label, c3, c4 in rows:
        body += text(20, y + 30, label, 13, INK, weight="bold")
        for k, (name, v, col) in enumerate([("c3 share of c0..c3", c3, "#8c959f"),
                                            ("c4 share of c0..c4", c4, "#d23b3b")]):
            yy = y + k * 26
            body += f'<rect x="{x0}" y="{yy}" width="{v * scale:.1f}" height="20" fill="{col}"/>'
            body += text(x0 + v * scale + 8, yy + 15, f"{v:.1f}x", 12, INK)
        y += 72
    return svg(W, H, body)

def main():
    if len(sys.argv) > 1:
        print("usage: python3 make_figures.py   (writes docs/channels.svg, docs/red_green.svg)")
        sys.exit(1)
    data = [(label, step_medians(path)) for label, path in RUNS]
    os.makedirs(os.path.join(HERE, "docs"), exist_ok=True)
    for name, fig in [("channels.svg", channels_figure(data)),
                      ("red_green.svg", red_green_figure(data))]:
        with open(os.path.join(HERE, "docs", name), "w") as f:
            f.write(fig)
        print("wrote docs/" + name)

if __name__ == "__main__":
    main()

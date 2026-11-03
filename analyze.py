#!/usr/bin/env python3
# Turn an als_probe.py CSV into the README table: for each step, the median of
# the second half of its samples (the first half may still be settling or the
# screen may not be in place yet), and each channel's share of c0..c4.
#
# Usage:
#   python3 analyze.py out.csv
#   python3 analyze.py out.csv --subtract-cover    # subtract the cover step first
#
# Steps are consecutive runs of the same phase label, so a repeated baseline is
# reported twice. Standard library only.

import csv, statistics, sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) != 1:
    print("usage: python3 analyze.py out.csv [--subtract-cover]")
    sys.exit(1)
subtract = "--subtract-cover" in sys.argv

steps = []                                   # [(phase, [row, ...]), ...]
try:
    f = open(args[0], newline="")
except OSError as e:
    print(f"cannot read {args[0]}: {e.strerror}")
    sys.exit(1)
with f:
    for r in csv.DictReader(f):
        if r["c0"] == "":                    # undecoded report length
            continue
        if not steps or steps[-1][0] != r["phase"]:
            steps.append((r["phase"], []))
        steps[-1][1].append(r)
if not steps:
    print("no decoded rows (empty file, or no 122-byte reports)")
    sys.exit(1)

def medians(rows):
    half = rows[len(rows) // 2:]
    ch = [statistics.median(float(r[f"c{i}"]) for r in half) for i in range(5)]
    lux = statistics.median(float(r["lux"]) for r in half)
    return ch, lux, len(half)

cover = None
if subtract:
    cov = [rows for p, rows in steps if p.lower().startswith("cover")]
    if not cov:
        print("no cover step to subtract")
        sys.exit(1)
    cover = medians(cov[0])[0]
    print("channels: step minus cover, signed. ratio: share of the positive part "
          "only. lux: not subtracted.")

print(f"{'step':<14}{'n':>4}  {'c0':>7}{'c1':>7}{'c2':>7}{'c3':>7}{'c4':>7}  {'lux':>7}  "
      f"ratio c0..c4         peak")
for phase, rows in steps:
    ch, lux, n = medians(rows)
    if cover:
        ch = [c - b for c, b in zip(ch, cover)]
    pos = [max(c, 0.0) for c in ch]
    total = sum(pos)
    ratio = [c / total if total else 0.0 for c in pos]
    peak = f"c{ratio.index(max(ratio))}" if total else "-"
    print(f"{phase[:14]:<14}{n:>4}  " + "".join(f"{c:>7.0f}" for c in ch)
          + f"  {lux:>7.1f}  " + " ".join(f"{x:.2f}" for x in ratio) + f"  {peak}")

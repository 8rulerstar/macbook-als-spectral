#!/usr/bin/env python3
# Live view of the five als color channels, with a guess at what is in front of
# the sensor: a red, green, blue or white phone screen, a covered sensor, or room
# light. Standard library only.
#
# Usage:
#   python3 color_live.py              # Ctrl-C to quit
#
# Hold a solid-color phone screen flat against the sensor (next to the webcam).
# The guess uses channel ratios with wide margins fitted to three runs on one
# Mac16,8 with phone OLED screens (see README); it is a rule of thumb, not a
# calibrated color measurement.

import os, signal, statistics, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from als_decode import decode_report
from als_hid import open_als, pump, warn_if_unverified_model

BAR = 24                                     # bar width in characters
ANSI = {"c0": "34", "c1": "36", "c2": "32", "c3": "33", "c4": "31"}
LABEL_COLOR = {"RED": "31", "GREEN": "32", "BLUE": "34", "WHITE": "37",
               "COVERED": "90", "ROOM": "0"}

def guess(ch, room_sum):
    """Classify one smoothed reading. room_sum: c0..c4 sum of room light at start."""
    c0, c1, c2, c3, c4 = ch
    total = sum(ch)
    c2 = max(c2, 1.0)
    if c4 / c2 > 1.5:
        return "RED"
    if c0 / c2 > 4:
        return "BLUE"
    if c0 / c2 < 0.5 and c4 / c2 < 0.4:
        return "GREEN"
    if total < 0.6 * room_sum:
        return "COVERED"
    if total > 1.5 * room_sum:
        return "WHITE"
    return "ROOM"

def bars(ch):
    total = sum(ch) or 1
    lines = []
    for i, v in enumerate(ch):
        share = v / total
        n = round(share * BAR / 0.7)         # 0.7 share fills the bar
        lines.append(f"  c{i} \033[{ANSI[f'c{i}']}m{'█' * min(n, BAR):<{BAR}}\033[0m {share:4.2f}")
    return lines

def main():
    if len(sys.argv) > 1:
        print("usage: python3 color_live.py")
        sys.exit(1)
    warn_if_unverified_model()
    recent = []
    def on_report(b):
        r = decode_report(b)
        if r:
            recent.append(r[0])
            del recent[:-5]                  # median of the last 5 reports
    open_als(on_report)

    stop = [False]
    signal.signal(signal.SIGINT, lambda *a: stop.__setitem__(0, True))

    print("Measuring room light for 3 s. Keep the sensor uncovered...")
    end = time.time() + 3
    room = []
    while time.time() < end and not stop[0]:
        pump(0.1)
        if recent:
            room.append(sum(recent[-1]))
    if not room:
        print("no reports received from the sensor.")
        sys.exit(1)
    room_sum = statistics.median(room)
    print("Now hold a red, green, blue or white phone screen against the sensor.\n")

    shown = 0
    while not stop[0]:
        pump(0.2)
        if len(recent) < 3:
            continue
        ch = [statistics.median(r[i] for r in recent) for i in range(5)]
        label = guess(ch, room_sum)
        out = [f"  \033[1;{LABEL_COLOR[label]}m{label:<8}\033[0m  "
               f"(c4/c2 {ch[4] / max(ch[2], 1):4.2f}, c0/c2 {ch[0] / max(ch[2], 1):4.2f})"]
        out += bars(ch)
        if shown:
            sys.stdout.write(f"\033[{shown}A")   # redraw in place
        sys.stdout.write("\n".join(l + "\033[K" for l in out) + "\n")
        sys.stdout.flush()
        shown = len(out)
    print("\nbye")

if __name__ == "__main__":
    main()

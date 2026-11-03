#!/usr/bin/env python3
# Read the MacBook ambient-light sensor (als) HID report and log its spectral
# channels through a color test. Standard library only (ctypes + IOKit).
#
# Usage:
#   python3 als_probe.py out.csv           # steps advance on a timer
#   python3 als_probe.py out.csv --wait    # press Enter before each step
#
# Summarize the CSV with: python3 analyze.py out.csv
#
# Requires Python 3.8+ on an Apple Silicon MacBook. Opening the HID device may
# need Input Monitoring permission for your terminal (System Settings, Privacy
# and Security, Input Monitoring), or running under sudo. If the device cannot
# be opened the script prints an error and exits.
#
# Report layout: 122-byte report, 5 uint32 spectral channels at bytes 20..39,
# float lux at bytes 40..43. Color-tested on macOS 27.0.1 and 27.2 (26B123).
# On any other length this script does NOT decode channels; it prints a warning
# and logs the raw hex.

import time, sys, os, csv, signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from als_decode import decode_report
from als_hid import open_als, pump, warn_if_unverified_model

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) != 1:
    print("usage: python3 als_probe.py out.csv [--wait]")
    sys.exit(1)
out = args[0]
unknown = [a for a in sys.argv[1:] if a.startswith("--") and a != "--wait"]
if unknown:
    print("unknown option:", " ".join(unknown))
    sys.exit(1)
wait = "--wait" in sys.argv
warn_if_unverified_model()

# Color test phases: hold a solid-color screen (e.g. a phone) against the sensor
# next to the webcam during each window. Each phase runs for a few seconds.
# With --wait: seconds dropped after Enter, then seconds recorded per step.
SETTLE = 3
WAIT_SECONDS = 10

PHASES = [
    ("baseline", 5),
    ("cover the sensor (finger next to the webcam)", 5),
    ("red screen", 6),
    ("green screen", 6),
    ("blue screen", 6),
    ("white screen", 6),
    ("flashlight (phone LED)", 6),
    ("baseline", 5),
]

rows = []
t0 = [None]
cur = [""]
warned = [False]

def decode(b):
    n = len(b)
    r = decode_report(b)                      # verified on 27.0.1 and 27.2
    if r:
        return r
    # Other lengths: layout unknown. Do not guess.
    if not warned[0]:
        warned[0] = True
        print(f"\n  WARNING: report is {n} bytes, not the 122-byte layout this "
              f"script decodes.")
        print("  Channels are NOT decoded for this length. Logging raw hex only.")
    return [None] * 5, None

drop = [False]
def on_report(b):
    if drop[0]:
        return
    ch, lux = decode(b)
    rows.append([round(time.time() - t0[0], 2), cur[0],
                 *ch, (round(lux, 1) if lux is not None else ""), b.hex()])
open_als(on_report)

def save():
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "phase", "c0", "c1", "c2", "c3", "c4", "lux", "hex"])
        w.writerows(rows)

# Ctrl-C can land inside the ctypes callback, where the exception is swallowed.
# Set a flag instead and stop from the main loop.
stop = [False]
signal.signal(signal.SIGINT, lambda *a: stop.__setitem__(0, True))

t0[0] = time.time()
try:
    for name, sec in PHASES:
        if wait:
            # Default Ctrl-C handling while blocked on input().
            signal.signal(signal.SIGINT, signal.default_int_handler)
            input(f"\nnext: {name}. Get ready, then press Enter ")
            signal.signal(signal.SIGINT, lambda *a: stop.__setitem__(0, True))
            # Drop reports during a short countdown: those queued while waiting
            # describe the previous light, and the next ones catch the screen
            # being put in place. Then record for longer than in timer mode.
            drop[0] = True
            for n in range(SETTLE, 0, -1):
                print(f"  hold still... {n}", flush=True)
                t_end = time.time() + 1
                while time.time() < t_end:
                    if stop[0]:
                        raise KeyboardInterrupt
                    pump(0.1)
            drop[0] = False
            sec = WAIT_SECONDS
        cur[0] = name
        print(f"\n>>> {name}: recording {sec}s, keep it steady", flush=True)
        end = time.time() + sec
        last = 0
        while time.time() < end:
            if stop[0]:
                raise KeyboardInterrupt
            pump(0.1)
            if rows and time.time() - last > 1:
                last = time.time()
                r = rows[-1]
                print("   ch", r[2:7], "lux", r[7], flush=True)
except (KeyboardInterrupt, EOFError):
    save()
    print("\ninterrupted. saved partial data:", out)
    sys.exit(130)
save()
if not rows:
    print("\nWARNING: no reports were received. The CSV has only a header.")
print("\ndone. saved:", out)

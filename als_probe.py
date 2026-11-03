#!/usr/bin/env python3
# Read the MacBook ambient-light sensor (als) HID report and log its spectral
# channels through a color test. Standard library only (ctypes + IOKit).
#
# Usage:
#   python3 als_probe.py out.csv
#
# Requires Python 3.8+ on an Apple Silicon MacBook. Opening the HID device may
# need Input Monitoring permission for your terminal (System Settings, Privacy
# and Security, Input Monitoring), or running under sudo. If the device cannot
# be opened the script stops at the assert below.
#
# Report layout is macOS-version specific:
#   macOS 27.0.1, 122-byte report: 5 uint32 spectral channels at bytes 20..39,
#     float lux at bytes 40..43. This is the layout decoded and color-tested in
#     the README.
#   macOS 27.2, 137-byte report: the fields became float32 and the offsets moved
#     (channels appear near bytes 28..47, not yet color-verified). On a 137-byte
#     report this script does NOT decode channels; it prints a warning and logs
#     the raw hex so you can investigate. See the README note on 27.2.

import ctypes, ctypes.util, struct, time, sys, csv

if len(sys.argv) < 2:
    print("usage: python3 als_probe.py out.csv")
    sys.exit(1)
out = sys.argv[1]

iokit = ctypes.CDLL(ctypes.util.find_library("IOKit"))
cf = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
V = ctypes.c_void_p
for f, r, a in [
    ("IOServiceMatching", V, [ctypes.c_char_p]),
    ("IOServiceGetMatchingServices", ctypes.c_int, [ctypes.c_uint, V, ctypes.POINTER(ctypes.c_uint)]),
    ("IOIteratorNext", ctypes.c_uint, [ctypes.c_uint]),
    ("IOHIDDeviceCreate", V, [V, ctypes.c_uint]),
    ("IOHIDDeviceOpen", ctypes.c_int, [V, ctypes.c_uint]),
    ("IOHIDDeviceScheduleWithRunLoop", None, [V, V, V]),
    ("IOHIDDeviceRegisterInputReportCallback", None, [V, V, ctypes.c_long, V, V]),
    ("IORegistryEntryCreateCFProperty", V, [ctypes.c_uint, V, V, ctypes.c_uint]),
]:
    fn = getattr(iokit, f); fn.restype = r; fn.argtypes = a
cf.CFStringCreateWithCString.restype = V
cf.CFStringCreateWithCString.argtypes = [V, ctypes.c_char_p, ctypes.c_uint]
cf.CFStringGetCString.argtypes = [V, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint]
cf.CFRunLoopGetCurrent.restype = V
cf.CFRunLoopRunInMode.argtypes = [V, ctypes.c_double, ctypes.c_bool]
S = lambda s: cf.CFStringCreateWithCString(None, s.encode(), 0x08000100)
mode = V.in_dll(cf, "kCFRunLoopDefaultMode")

# Color test phases: hold a solid-color screen (e.g. a phone) against the sensor
# next to the webcam during each window. Each phase runs for a few seconds.
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
    if n == 122:                              # macOS 27.0.1, verified
        ch = list(struct.unpack_from("<5I", b, 20))
        lux = struct.unpack_from("<f", b, 40)[0]
        return ch, lux
    # Other lengths (e.g. 137-byte on macOS 27.2): layout differs. Do not guess.
    if not warned[0]:
        warned[0] = True
        print(f"\n  WARNING: report is {n} bytes, not the 122-byte layout this "
              f"script decodes (macOS 27.0.1).")
        print("  Channels are NOT decoded for this length. Logging raw hex only. "
              "See the README note on macOS 27.2.")
    return [None] * 5, None

CB = ctypes.CFUNCTYPE(None, V, ctypes.c_int, V, ctypes.c_int, ctypes.c_uint,
                      ctypes.POINTER(ctypes.c_uint8), ctypes.c_long)
def cb(ctx, res, snd, typ, rid, rep, ln, *a):
    b = bytes(rep[:ln])
    ch, lux = decode(b)
    rows.append([round(time.time() - t0[0], 2), cur[0],
                 *ch, (round(lux, 1) if lux is not None else ""), b.hex()])
c = CB(cb)
buf = (ctypes.c_uint8 * 256)()

it = ctypes.c_uint()
iokit.IOServiceGetMatchingServices(0, iokit.IOServiceMatching(b"AppleSPUHIDDevice"),
                                   ctypes.byref(it))
found = False
while (s := iokit.IOIteratorNext(it)):
    p = iokit.IORegistryEntryCreateCFProperty(s, S("Product"), None, 0)
    bb = ctypes.create_string_buffer(64)
    if p:
        cf.CFStringGetCString(p, bb, 64, 0x08000100)
    if bb.value == b"als":
        d = iokit.IOHIDDeviceCreate(None, s)
        assert iokit.IOHIDDeviceOpen(d, 0) == 0, "IOHIDDeviceOpen failed (grant Input Monitoring or run with sudo)"
        iokit.IOHIDDeviceRegisterInputReportCallback(d, buf, 256, ctypes.cast(c, V), None)
        iokit.IOHIDDeviceScheduleWithRunLoop(d, cf.CFRunLoopGetCurrent(), mode)
        found = True
        break
if not found:
    print("als device not found under AppleSPUHIDDevice. Nothing to read.")
    sys.exit(1)

t0[0] = time.time()
for name, sec in PHASES:
    cur[0] = name
    print(f"\n>>> {name} ({sec}s)", flush=True)
    end = time.time() + sec
    last = 0
    while time.time() < end:
        cf.CFRunLoopRunInMode(mode, 0.1, False)
        if rows and time.time() - last > 1:
            last = time.time()
            r = rows[-1]
            print("   ch", r[2:7], "lux", r[7], flush=True)

with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["t", "phase", "c0", "c1", "c2", "c3", "c4", "lux", "hex"])
    w.writerows(rows)
print("\ndone. saved:", out)

# Open the MacBook als HID device and deliver its input reports to a callback.
# Shared by als_probe.py and color_live.py. Standard library only (ctypes + IOKit).
#
# Opening the device may need Input Monitoring permission for your terminal
# (System Settings, Privacy and Security, Input Monitoring), or sudo.

import ctypes, ctypes.util, subprocess, sys

# The decode was verified on one machine. Other models may share the 122-byte
# length with a different field layout, so say so instead of decoding silently.
VERIFIED_MODELS = {"Mac16,8"}

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

CB = ctypes.CFUNCTYPE(None, V, ctypes.c_int, V, ctypes.c_int, ctypes.c_uint,
                      ctypes.POINTER(ctypes.c_uint8), ctypes.c_long)
_keep = []                                   # callback and buffer must outlive the run loop

def warn_if_unverified_model():
    try:
        model = subprocess.run(["sysctl", "-n", "hw.model"], capture_output=True,
                               text=True).stdout.strip()
    except OSError:
        model = ""
    if model not in VERIFIED_MODELS:
        print(f"NOTE: model {model or 'unknown'} is not one the decode was verified on "
              f"({', '.join(sorted(VERIFIED_MODELS))}). Check the channel values make sense.")

def open_als(on_report):
    """Call on_report(bytes) for every als input report. Exits if not available."""
    c = CB(lambda ctx, res, snd, typ, rid, rep, ln, *a: on_report(bytes(rep[:ln])))
    buf = (ctypes.c_uint8 * 256)()
    _keep.extend([c, buf])
    it = ctypes.c_uint()
    iokit.IOServiceGetMatchingServices(0, iokit.IOServiceMatching(b"AppleSPUHIDDevice"),
                                       ctypes.byref(it))
    while (s := iokit.IOIteratorNext(it)):
        p = iokit.IORegistryEntryCreateCFProperty(s, S("Product"), None, 0)
        bb = ctypes.create_string_buffer(64)
        if p:
            cf.CFStringGetCString(p, bb, 64, 0x08000100)
        if bb.value == b"als":
            d = iokit.IOHIDDeviceCreate(None, s)
            if not d or iokit.IOHIDDeviceOpen(d, 0) != 0:
                print("IOHIDDeviceOpen failed (grant Input Monitoring or run with sudo)")
                sys.exit(1)
            iokit.IOHIDDeviceRegisterInputReportCallback(d, buf, 256, ctypes.cast(c, V), None)
            iokit.IOHIDDeviceScheduleWithRunLoop(d, cf.CFRunLoopGetCurrent(), mode)
            return
    print("als device not found under AppleSPUHIDDevice. Nothing to read.")
    sys.exit(1)

def pump(seconds):
    """Run the run loop so queued reports reach the callback."""
    cf.CFRunLoopRunInMode(mode, seconds, False)

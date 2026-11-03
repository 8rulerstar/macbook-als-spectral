# Decode one MacBook als HID input report. Shared by als_probe.py and the tests.
#
# 122-byte report: 5 uint32 spectral channels at bytes 20..39, float lux at
# bytes 40..43. Color-tested on macOS 27.0.1 and 27.2 (26B123), Mac16,8.

import struct

REPORT_LEN = 122

def decode_report(b):
    """Return (channels c0..c4, lux) for a 122-byte report, or None otherwise."""
    if len(b) != REPORT_LEN:
        return None
    ch = list(struct.unpack_from("<5I", b, 20))
    lux = struct.unpack_from("<f", b, 40)[0]
    return ch, lux

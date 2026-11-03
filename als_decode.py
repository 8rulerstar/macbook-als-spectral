# Decode one MacBook als HID input report. Shared by the scripts and the tests.
#
# 122-byte report, little-endian. Color-tested on macOS 27.0.1 and 27.2 (26B123),
# Mac16,8. See the README byte table for how sure each field is.

import struct

REPORT_LEN = 122

def decode_report(b):
    """Return (channels c0..c4, lux) for a 122-byte report, or None otherwise."""
    if len(b) != REPORT_LEN:
        return None
    ch = list(struct.unpack_from("<5I", b, 20))
    lux = struct.unpack_from("<f", b, 40)[0]
    return ch, lux

def decode_fields(b):
    """Return every field identified so far as a dict, or None for other lengths."""
    if len(b) != REPORT_LEN:
        return None
    ch, lux = decode_report(b)
    return {
        "report_id": b[0],                                 # 0xEC
        "seq": struct.unpack_from("<I", b, 1)[0],           # +1 per report
        "timestamp_us": struct.unpack_from("<Q", b, 5)[0],  # microseconds, likely since boot
        "channels": ch,
        "lux": lux,
        "const19": struct.unpack_from("<I", b, 63)[0],      # always 19, meaning unknown
        "mode": b[67],                                      # 0x40, once 0x20 under bright light
        "cct": struct.unpack_from("<f", b, 69)[0],          # likely color temperature (K)
        "config": struct.unpack_from("<2I", b, 73),         # two equal values, changed with OS
    }

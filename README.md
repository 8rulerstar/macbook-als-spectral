# Decoding the MacBook ambient-light sensor, and the spectral channel public tools drop

The Apple Silicon MacBook "ambient light sensor" (`als`) reports more than lux:
on macOS 27.0.1 its HID report carries a block of spectral channels (chip:
STMicroelectronics VD6286). This note decodes that report, shows by a color test
that the channels are ordered by wavelength, and points out that existing public
tools read only four of the five channels. I opened a pull request adding the
missing channel.

Measured on a MacBook Pro Mac16,8 (M4 Pro).

> Note on macOS version: the verified decode below is from **macOS 27.0.1**
> (122-byte report). On **macOS 27.2** the report changed to 137 bytes and the
> fields became `float32` at shifted offsets, so the byte offsets here do not
> apply there. See "macOS 27.2 changed the report" at the end. The decode and
> the pull request target the 27.0.1 layout.

## What the als report contains (macOS 27.0.1, 122-byte report)

- bytes **20..39**: five little-endian `uint32` spectral channels (c0..c4).
- bytes **40..43**: `float32` lux.

```python
import struct
channels = struct.unpack_from("<5I", report, 20)   # c0..c4
lux      = struct.unpack_from("<f",  report, 40)[0]
```

`MaxInputReportSize` for the `als` node is 122 (from `ioreg`), matching the
122-byte report.

## The channels are ordered by wavelength (color test)

I lit the sensor with solid colors from a phone screen and measured each
channel's response (median of the second half of each step, normalized to a
channel ratio):

| screen color | peak channel | c0 | c1 | c2 | c3 | c4 |
|---|---|---|---|---|---|---|
| blue  | **c0** | 0.58 | 0.28 | 0.07 | 0.04 | 0.03 |
| green | **c2** | 0.08 | 0.21 | 0.40 | 0.20 | 0.10 |
| red   | **c4** | 0.15 | 0.13 | 0.17 | 0.22 | 0.34 |
| white | flat   | 0.24 | 0.22 | 0.25 | 0.14 | 0.15 |

- The peak channel moves c0 (blue) to c2 (green) to c4 (red), i.e. the channels
  run in wavelength order. Under green, the neighboring channels c1 and c3 rise
  together, consistent with that ordering.
- The red separation is the softest (under red, c4 peaks at 0.34 but c0 is 0.15);
  a phone OLED red is not a narrow line, so treat red as the weakest leg of the
  ordering.

## The channel block really is five wide (driver struct)

Because "five channels" is my reading of the bytes, I cross-checked it against
Apple's driver symbols. The vendor-data type encoding of `AppleSPUVD6286`
(seen in public kext symbol dumps) is:

```
alsdefines_vendorvd6286_s = I [5i][5i][5s] f I f I I f I [5I]
```

The `[5i]` and `[5I]` arrays are five wide, consistent with five channels.
I did not establish which of those arrays the bytes 20..39 correspond to, only
that a five-channel block is what the driver describes and what I measured.

## What existing public tools read

Two public tools read this sensor. On the 122-byte layout both read only the
first four channels and skip the fifth:

- **olvvier/apple-silicon-accelerometer** (Python; the package is named
  `macimu`): `macimu/__init__.py` uses channel offsets `[20, 24, 28, 32]`, i.e.
  four channels, dropping offset 36.
- **junwatu/macimu** (Swift): reads offsets 20/24/28/32, same four, skipping 36.

So on this layout the fifth channel (offset 36) is present in the report but not
read. I opened a pull request to add it:
**olvvier/apple-silicon-accelerometer#25** ("read_als: include the 5th spectral
channel at offset 36").

Note this is a layout-specific point: it holds for the 122-byte report
(27.0.1). On 27.2 the format changed (below), so the specific offset-36 claim is
tied to 27.0.1.

## Quick start

```
# Python 3.8+, Apple Silicon MacBook
python3 als_probe.py out.csv
```

- The script finds the `als` HID device and runs an eight-step color sequence
  (baseline, cover, red, green, blue, white, flashlight, baseline). When a step
  prints, hold the matching solid-color screen against the sensor (next to the
  webcam) for the few seconds of that step. Prepare the color images in advance.
- Output `out.csv` columns: `t, phase, c0..c4, lux, hex`.
- Permissions: opening the HID device may require Input Monitoring for your
  terminal (System Settings, Privacy and Security, Input Monitoring), or `sudo`.
  If it cannot open, the script stops with an assertion.
- The script decodes channels only for the 122-byte report. On a 137-byte report
  (27.2) it prints a warning and logs raw hex only.

## macOS 27.2 changed the report

On macOS 27.2 (26B123) the `als` report is 137 bytes, not 122, and the numeric
fields are `float32` rather than `uint32`. Reading the 122-byte offsets there
yields garbage. From a structural scan of the 137-byte report, five consecutive
`float32` values appear near bytes 28..47, with other float fields around bytes
20 and 52 (one near 5100, plausibly a color temperature). I have not re-run the
color test on 27.2, so which float is which channel is not verified. Treat the
27.2 layout as provisional and the 27.0.1 decode above as the verified one.

## Honest limits

- No absolute calibration of lux or the channels (relative ratios only).
- Channel center wavelengths are not confirmed against a datasheet; only the
  ordering is established by measurement, and the red leg is the weakest.
- "Five channels" is what this report and the driver struct expose. I did not
  confirm the VD6286 channel count against a datasheet; the related VD6283 is
  documented as a 6-channel color sensor, so a separate clear or IR channel at
  another offset is not ruled out.
- Single machine (Mac16,8), and the layout is OS-version specific (122-byte on
  27.0.1, 137-byte on 27.2).

## Reproduce

Standard library only (`ctypes` + IOKit), no external dependencies. See
`als_probe.py`.

## License

MIT. See `LICENSE`.

## Author

Byungkun Jang

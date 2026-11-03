# Decoding the MacBook ambient-light sensor, and the fifth spectral channel two public tools do not read

The Apple Silicon MacBook "ambient light sensor" (`als`) reports more than lux:
on macOS 27.0.1 and 27.2 its HID report carries a block of spectral channels (the driver is
named `AppleSPUVD6286`, suggesting an ST VD6286; not confirmed from a datasheet). This note decodes that report, shows by a color test
that c0, c2 and c4 respond most to blue, green and red, consistent with
wavelength order, and points out that two public tools I checked read only
four of the five channels. I opened a pull request adding the
missing channel.

Measured on a MacBook Pro Mac16,8 (M4 Pro).

> Note on macOS version: the decode below is the 122-byte report. It was
> color-tested on **macOS 27.0.1** and again on **macOS 27.2** (26B123). A
> 137-byte report was observed once earlier on 27.2 and is not decoded. See
> "macOS 27.2" at the end.

## What the als report contains (122-byte report)

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
channel ratio). This table is from macOS 27.0.1; the 27.2 repeat is at the end:

| screen color | peak channel | c0 | c1 | c2 | c3 | c4 |
|---|---|---|---|---|---|---|
| blue  | **c0** | 0.58 | 0.28 | 0.07 | 0.04 | 0.03 |
| green | **c2** | 0.08 | 0.21 | 0.40 | 0.20 | 0.10 |
| red   | **c4** | 0.15 | 0.13 | 0.17 | 0.22 | 0.34 |
| white | broad  | 0.24 | 0.22 | 0.25 | 0.14 | 0.15 |

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

Two public tools I checked read this sensor. On the 122-byte layout both read
only the first four channels:

- **olvvier/apple-silicon-accelerometer** (Python; the package is named
  `macimu`): `macimu/__init__.py` uses channel offsets `[20, 24, 28, 32]`, i.e.
  four channels, not offset 36.
- **junwatu/macimu** (Swift): reads offsets 20/24/28/32, the same four.

So on this layout the fifth channel (offset 36) is present in the report but not
read. I opened a pull request to add it:
**olvvier/apple-silicon-accelerometer#25** ("read_als: include the 5th spectral
channel at offset 36").

Note this is a layout-specific point: it holds for the 122-byte report
(seen on 27.0.1 and 27.2). It does not apply to the 137-byte report noted below.

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
  If it cannot open, the script prints an error and exits.
- Steps advance on a timer with no pause between them. Ctrl-C saves the rows
  collected so far.
- The script decodes channels only for the 122-byte report. On any other length
  it prints a warning and logs raw hex only.

## macOS 27.2

On macOS 27.2 (26B123) I repeated the color test. All 217 reports were 122
bytes, and the same decode (uint32 c0..c4 at bytes 20..39, float lux at 40)
gives the same wavelength order:

| screen color | peak channel | c0 | c1 | c2 | c3 | c4 |
|---|---|---|---|---|---|---|
| blue  | **c0** | 0.62 | 0.27 | 0.05 | 0.03 | 0.02 |
| green | **c2** | 0.08 | 0.20 | 0.44 | 0.21 | 0.07 |
| red   | **c4** | 0.13 | 0.10 | 0.15 | 0.21 | 0.41 |
| white | broad  | 0.31 | 0.21 | 0.24 | 0.13 | 0.10 |

Red is again the weakest leg: under red the raw counts were small (c4 about 715,
lux about 50) versus green (c2 about 11850, lux about 830).

Earlier on the same OS version I captured a 137-byte report whose fields looked
like `float32` at shifted offsets. It did not appear in this run, and I have not
established when it occurs or what its layout is. The script does not decode it.

## Honest limits

- No absolute calibration of lux or the channels (relative ratios only).
- Channel center wavelengths are not confirmed against a datasheet; only the
  ordering is established by measurement, and the red leg is the weakest.
- "Five channels" is what this report and the driver struct expose. I did not
  confirm the VD6286 channel count against a datasheet; the related VD6283 is
  documented as a 6-channel color sensor, so a separate clear or IR channel at
  another offset is not ruled out.
- Single machine (Mac16,8). The 122-byte layout was verified on 27.0.1 and 27.2;
  the 137-byte report seen once on 27.2 is not understood.

## Reproduce

Standard library only (`ctypes` + IOKit), no external dependencies. See
`als_probe.py`.

## License

MIT. See `LICENSE`.

## Author

Byungkun Jang

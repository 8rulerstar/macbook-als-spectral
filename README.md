# The MacBook ambient light sensor is a 5-channel spectral sensor

Decoding the `als` HID report on Apple Silicon MacBooks, and what the channels mean.

Measured on a MacBook Pro Mac16,8 (M4 Pro), macOS 27.0.1.

## Summary

The MacBook "ambient light sensor" (`als`) is not a plain lux meter. It is a
5-channel spectral sensor (STMicroelectronics VD6286), and the channels are laid
out in wavelength order (blue to red). Existing public tools either drop one of
these channels (the red band) or read only the lux value and discard the
spectral channels entirely. The hardware exposes 5 spectral channels; the
information is lost at the consumer-tool layer, not at the sensor.

## Background

The SPU (Sensor Processing Unit) on Apple Silicon MacBooks exposes several
sensors over HID (`ioreg -c AppleSPUHIDDevice`: `accel`, `gyro`, `als`,
`las` (lid angle), and others). `als` is usually treated as "ambient light
sensor = lux." Looking at the actual report, lux is only part of it: a block of
spectral channels precedes it.

The chip is the STMicroelectronics **VD6286** (Apple driver `AppleSPUVD6286`,
codename "Redbird"). Asahi Linux handles the same part in its `aop_als` kernel
module.

## Report format (decoded by measurement)

- `als` input report: 122 bytes (137 bytes on some units; the fields below are
  from the 122-byte layout measured here).
- bytes **20..39**: five little-endian `uint32` values (spectral channels c0..c4).
- bytes **40..43**: `float32` (lux).

```python
import struct
channels = struct.unpack_from("<5I", report, 20)   # c0..c4
lux      = struct.unpack_from("<f",  report, 40)[0]
```

## What the channels are (color test)

I lit the sensor with solid colors from a phone screen and measured each
channel's response (median of the second half of each step, normalized to a
channel ratio):

| screen color | peak channel | c0 | c1 | c2 | c3 | c4 |
|---|---|---|---|---|---|---|
| blue  | **c0** | 0.58 | 0.28 | 0.07 | 0.04 | 0.03 |
| green | **c2** | 0.08 | 0.21 | 0.40 | 0.20 | 0.10 |
| red   | **c4** | 0.15 | 0.13 | 0.17 | 0.22 | 0.34 |
| white | even   | 0.24 | 0.22 | 0.25 | 0.14 | 0.15 |

- The channels are in **wavelength order**: c0 (blue) to c2 (green) to c4 (red).
  Under green, the neighboring channels c1 and c3 rise together, consistent with
  that ordering.
- So this is a color / spectral sensor, and the channels carry information usable
  for color-temperature (white-balance) estimation, not just brightness.

## Cross-check: Apple driver struct

Because "5 channels" could be my interpretation of the bytes, I cross-checked it
against Apple's own driver symbols. The reverse-engineered vendor-data type
encoding of `AppleSPUVD6286` is:

```
alsdefines_vendorvd6286_s = I [5i][5i][5s] f I f I I f I [5I]
```

`[5i]` and `[5I]` are arrays of **five**. Apple's own struct confirms the sensor
emits 5 channels, matching the 5 channels I measured. (Visible in public kext
symbol diffs.)

## What existing public tools miss

- **macimu** (Swift, macOS): reads only **four** color channels, at offsets
  20/24/28/32, and skips the fifth (offset 36, the red band).
- **Asahi Linux `aop_als`** (kernel): reads only **lux** (offset 0x28), no color
  channels. That is fine for auto-brightness, which is its purpose, but the
  spectral information is discarded.

## Reproduce

Standard-library `ctypes` + IOKit only, no external dependencies. See
`als_probe.py`. Measured on MacBook Pro Mac16,8 (M4 Pro), macOS 27.0.1.

## Upstream

I opened a pull request adding the fifth channel to one of these tools:
read_als: include the 5th spectral channel at offset 36
(olvvier/apple-silicon-accelerometer#25).

## Honest limits

- No absolute calibration of lux or the channels (relative ratios only). The
  unit scale is not established.
- The exact center wavelength of each channel is not confirmed against a
  datasheet; only the wavelength ordering is established by measurement.
- The VD6286 struct has several 5-element arrays (`[5i]`, `[5I]`); which is raw
  versus calibrated is not determined. I did not map the offset-20..39 block I
  read to a specific one of those arrays, only confirmed it is the block that
  shows a color response.

## Author

Byungkun Jang

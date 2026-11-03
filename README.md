# The MacBook light sensor has five color channels. Two public tools read four.

The Apple Silicon MacBook ambient light sensor (`als`) reports more than lux. Its
HID report carries five color channels, c0..c4, which a color test shows
peaking from blue (c0) through green (c2) to red (c4). Two
public tools that read this sensor (as of 2026-11-03) read only the first four.
The fifth channel, c4, is the one that separates red from green best.

![Red/green contrast of c3 vs c4](docs/red_green.svg)

This repository has a standard-library Python script that reads the raw
channels, the three color-test runs behind every number here, and the analysis
that reproduces them. I opened a pull request upstream to add the fifth channel
(olvvier/apple-silicon-accelerometer#25).

Measured on one MacBook Pro Mac16,8 (M4 Pro): one run on macOS 27.0.1, two on
27.2 (26B123).
The driver is named `AppleSPUVD6286`, suggesting an ST VD6286; not confirmed
from a datasheet.

## Quick start

```
# Python 3.8+, Apple Silicon MacBook
python3 als_probe.py out.csv --wait    # press Enter before each step
python3 analyze.py out.csv             # per-step medians and channel ratios
```

Before you start, put solid red, green, blue and white images on your phone and
turn its brightness up. The script runs eight steps (baseline, cover, red,
green, blue, white, flashlight, baseline). At each color step hold that screen
against the sensor, next to the webcam. At the cover step cover the sensor with
a finger; at the flashlight step shine the phone's LED at it.

<details>
<summary>More on the scripts</summary>

- Without `--wait`, all eight steps run back to back on a timer (about 45 s,
  5 to 6 s each), so have the screens ready. With `--wait`, each step waits for
  Enter, then counts down 3 s (reports in that window and while waiting are
  dropped, so moving the phone into place is not recorded), then records 10 s. In both modes Ctrl-C saves the rows
  collected so far.
- Output `out.csv` columns: `t, phase, c0..c4, lux, hex`.
- Permissions: opening the HID device may require Input Monitoring for your
  terminal (System Settings, Privacy and Security, Input Monitoring), or `sudo`.
  If it cannot open, the script prints an error and exits.
- On a model other than Mac16,8 the script prints a note that the decode is
  unverified there, then decodes anyway. Check the values look sensible.
- The script decodes channels only for the 122-byte report. On any other length
  it prints a warning and logs raw hex only.
- `analyze.py` prints, for each step, the median of the second half of its
  samples and each channel's share of c0..c4 (the method behind the tables
  here). `--subtract-cover` subtracts the cover step from the channels first and
  prints the signed differences; the ratio uses the positive part only and lux
  is not subtracted. A finger over the sensor is not a true dark reference (it
  passes some red), so read that mode with care.

</details>

## What the als report contains (122-byte report)

- bytes **20..39**: five little-endian `uint32` color channels (c0..c4).
- bytes **40..43**: `float32` lux.

```python
import struct
channels = struct.unpack_from("<5I", report, 20)   # c0..c4
lux      = struct.unpack_from("<f",  report, 40)[0]
```

`MaxInputReportSize` for the `als` node is 122 (from `ioreg`), matching the
122-byte report. The same layout was seen on macOS 27.0.1 and 27.2.

## Channel response follows wavelength order (color test)

I lit the sensor with solid colors from a phone screen and took, for each step,
the median of the second half of its samples, as a share of c0..c4:

![Channel share under each phone-screen color](docs/channels.svg)

- The peak channel moves c0 (blue) to c2 (green) to c4 (red), consistent with
  c0..c4 running in wavelength order. Under green, the neighboring channels c1
  and c3 rise together. The placement of c1 and c3 is inferred from this
  neighbor response only; three phone primaries cannot pin down all five.
- Across the three runs the peak channel is the same for every color. The blue
  and green rows agree within 0.06 per channel; the red row varies more (c4
  share 0.34 to 0.47), tracking how dark the cover step was.
- Red was the weakest leg in the first two runs, because the finger did not
  fully cover the sensor: with it "covered", lux was still about 158 (27.0.1)
  and 39 (27.2 run 1), and red c4 was only 3.2x and 2.1x the covered level. In
  27.2 run 2 the sensor was covered properly (lux about 19), each step got a 3 s
  settle before 10 s of recording, and red c4 was 2434 against 198 covered,
  12.3x. A phone OLED red is still not a narrow line.

<details>
<summary>Tables</summary>

macOS 27.0.1:

| screen color | peak channel | c0 | c1 | c2 | c3 | c4 |
|---|---|---|---|---|---|---|
| blue  | **c0** | 0.58 | 0.28 | 0.06 | 0.04 | 0.03 |
| green | **c2** | 0.08 | 0.21 | 0.40 | 0.20 | 0.10 |
| red   | **c4** | 0.15 | 0.12 | 0.17 | 0.22 | 0.34 |
| white | broad  | 0.24 | 0.22 | 0.25 | 0.14 | 0.15 |

macOS 27.2 (26B123) run 1, all 217 reports 122 bytes:

| screen color | peak channel | c0 | c1 | c2 | c3 | c4 |
|---|---|---|---|---|---|---|
| blue  | **c0** | 0.62 | 0.27 | 0.05 | 0.03 | 0.02 |
| green | **c2** | 0.08 | 0.20 | 0.44 | 0.21 | 0.07 |
| red   | **c4** | 0.13 | 0.10 | 0.15 | 0.21 | 0.41 |
| white | c0, broad | 0.31 | 0.21 | 0.24 | 0.13 | 0.10 |

macOS 27.2 (26B123) run 2, all 403 reports 122 bytes:

| screen color | peak channel | c0 | c1 | c2 | c3 | c4 |
|---|---|---|---|---|---|---|
| blue  | **c0** | 0.64 | 0.27 | 0.05 | 0.03 | 0.02 |
| green | **c2** | 0.10 | 0.21 | 0.43 | 0.20 | 0.06 |
| red   | **c4** | 0.10 | 0.08 | 0.13 | 0.22 | 0.47 |
| white | c0, broad | 0.34 | 0.22 | 0.23 | 0.12 | 0.08 |

With the cover step subtracted, the 27.2 run 1 red row becomes c3 86 and c4 376 with
c0..c2 slightly below the cover level, so the red signal there is only a few
hundred counts.

</details>

## Why the fifth channel matters

With only c0..c3, the most red-sensitive channel is c3. Its share under a red
screen is not far from its share under a green one. Adding c4 widens that gap
several times over (phone OLED screens, no cover subtraction):

| run | c3 share of c0..c3, red / green | c4 share of c0..c4, red / green |
|---|---|---|
| 27.0.1 | 0.33 / 0.22 (1.5x) | 0.34 / 0.10 (3.3x) |
| 27.2 run 1 | 0.36 / 0.22 (1.6x) | 0.41 / 0.07 (6.0x) |
| 27.2 run 2 | 0.41 / 0.21 (1.9x) | 0.47 / 0.06 (7.4x) |

(Multipliers use unrounded shares.) The c3 share is a simple 4-channel metric,
not the best one: c3/c2 alone already rises from about 0.5 under green to 1.3
to 1.7 under red, so four channels can tell red from green. Adding c4 still
widens the contrast (c4/c2: about 0.14 to 0.26 under green, 2.0 to 3.6 under
red), and of the five channels c4 has the largest red/green contrast in all
three runs.

So the channel those tools do not read is the one that best separates red from
green. This is three runs with phone primaries, not a calibrated spectral
measurement.

## What existing public tools read

Two public tools I checked read this sensor (as of 2026-11-03). The Swift one
started as a port of the Python one, so this is one design, not two independent
findings. On the 122-byte layout both read only the first four channels, which
the Python package documents as "lux + 4 spectral channels":

- **olvvier/apple-silicon-accelerometer** (Python; the package is named
  `macimu`): [`macimu/__init__.py`](https://github.com/olvvier/apple-silicon-accelerometer/blob/203685640287449eaecf521c24d1f5e52486ecb7/macimu/__init__.py) uses channel offsets `[20, 24, 28, 32]`, i.e.
  four channels, not offset 36.
- **junwatu/macimu** (Swift): [`IMU.swift`](https://github.com/junwatu/macimu/blob/b8b4ebbaae54279bd3f3a5d9aef5b852f048cd4a/Sources/MacIMU/IMU.swift) reads offsets 20/24/28/32, the same four.

So on this layout the fifth channel (offset 36) is present in the report but not
read. I opened a pull request to add it:
**olvvier/apple-silicon-accelerometer#25** ("read_als: include the 5th spectral
channel at offset 36").

## Cross-check: the driver struct has five-wide arrays

<details>
<summary>Driver type encoding (a weak cross-check)</summary>

Because "five channels" is my reading of the bytes, I cross-checked it against
Apple's driver symbols. The `com.apple.driver.AppleALSColorSensor` kext carries
an Objective-C type encoding for its als report, and the VD6286 vendor-data
member is (source: the [blacktop/ipsw-diffs kext diff for macOS 27.0 betas
26A5378n vs 26A5388g](https://github.com/blacktop/ipsw-diffs/blob/ee7c537d56250c6157860d81cb27273fcb30aaa8/macOS/27_0_26A5378n_vs_27_0_26A5388g/KEXTS/com.apple.driver.AppleALSColorSensor.md)):

```
alsdefines_vendorvd6286_s = I [5i][5i][5s] f I f I I f I [5I]
```

The `[5i]` and `[5I]` arrays are five wide, consistent with five channels.
I did not establish which of those arrays the bytes 20..39 correspond to, only
that a five-channel block is what the driver describes and what I measured.
The same encoding also lists other vendor variants (for example a
`vendormorayfamily_s` with `[5f]` float arrays); which one a given machine uses
is not shown by the encoding. Five-wide arrays are not unique to VD6286 either
(`vendorct725_s` has `[5i][5s]`), so this is a weak cross-check.

</details>

## Honest limits

- No absolute calibration of lux or the channels (relative ratios only).
- Channel center wavelengths are not confirmed against a datasheet; only the
  ordering is established by measurement, and the red leg is the weakest.
- "Five channels" is what this report and the driver struct expose. I did not
  confirm the VD6286 channel count against a datasheet; the related VD6283 is
  documented as a 6-channel color sensor, so a separate clear or IR channel at
  another offset is not ruled out.
- Single machine (Mac16,8), three runs (one on 27.0.1, two on 27.2), phone OLED
  as the only colored light source. The 122-byte layout was verified on 27.0.1 and 27.2.

## Reproduce

Standard library only (`ctypes` + IOKit), no external dependencies.

All three runs behind the tables and figures are in `data/` (same columns as
`als_probe.py` output, raw report hex included):

- `data/macos27.0.1_mac16-8.csv`: eight steps including flashlight. The step
  labels were in Korean and have been translated to English; nothing else was
  changed.
- `data/macos27.2_mac16-8.csv`: taken with an earlier version of the script,
  seven steps (no flashlight) with labels such as `RED` and `cover sensor`.
- `data/macos27.2_mac16-8_run2.csv`: current script with `--wait` (3 s settle,
  10 s per step), sensor well covered (lux about 19 in the cover step).

```
python3 analyze.py data/macos27.0.1_mac16-8.csv
python3 analyze.py data/macos27.2_mac16-8.csv
python3 analyze.py data/macos27.0.1_mac16-8.csv --subtract-cover
python3 make_figures.py                  # redraws docs/*.svg
python3 -m unittest -v test_decode       # checks decode and the README numbers
```

Results from other Mac models are welcome as issues: include the model
(`sysctl -n hw.model`), the macOS version, and the `analyze.py` output.

## License

MIT. See `LICENSE`.

## Author

Byungkun Jang

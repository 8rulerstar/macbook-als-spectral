#!/usr/bin/env python3
# Render docs/demo.gif: a replay of a recorded run through color_live.py's
# display and guess. Not a live capture. Needs Pillow (not used by the repo).
#
# Usage: python3 tools/make_demo_gif.py .

import csv, os, statistics, sys
from PIL import Image, ImageDraw, ImageFont

repo = sys.argv[1]
sys.path.insert(0, repo)
from color_live import guess

RUN = os.path.join(repo, "data/macos27.2_mac16-8_run2.csv")
OUT = os.path.join(repo, "docs/demo.gif")
W, H = 760, 300
BG, FG, DIM = (22, 24, 29), (230, 232, 235), (130, 136, 145)
CH_COLOR = [(80, 130, 240), (60, 200, 210), (70, 190, 90), (230, 200, 60), (235, 80, 80)]
LABEL_COLOR = {"RED": (235, 80, 80), "GREEN": (70, 190, 90), "BLUE": (80, 130, 240),
               "WHITE": (240, 240, 240), "COVERED": (130, 136, 145), "ROOM": FG}
SWATCH = {"baseline": ((60, 62, 68), "room light"), "cover": ((10, 10, 12), "finger over sensor"),
          "red": ((255, 0, 0), "red screen"), "green": ((0, 255, 0), "green screen"),
          "blue": ((0, 0, 255), "blue screen"), "white": ((255, 255, 255), "white screen"),
          "flashlight": ((255, 250, 225), "phone LED")}
ORDER = ["baseline", "red", "green", "blue", "white", "cover"]
FRAMES_PER_STEP = 12

font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 17)
small = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 13)
big = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 26)

steps = {}
for r in csv.DictReader(open(RUN)):
    steps.setdefault(r["phase"].lower().split()[0], []).append(
        [float(r[f"c{i}"]) for i in range(5)])
room = statistics.median(sum(x) for x in steps["baseline"])

frames = []
for key in ORDER:
    samples = steps[key][len(steps[key]) // 2:]
    for f in range(FRAMES_PER_STEP):
        j = min(len(samples) - 1, f * len(samples) // FRAMES_PER_STEP + 4)
        recent = samples[max(0, j - 4):j + 1]
        ch = [statistics.median(x[i] for x in recent) for i in range(5)]
        label = guess(ch, room)
        im = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(im)
        col, name = SWATCH[key]
        d.rounded_rectangle([24, 40, 204, 240], 14, fill=col, outline=(90, 94, 100), width=2)
        d.text((114, 258), name, font=small, fill=DIM, anchor="mm")
        d.text((236, 28), "color_live.py display, replayed", font=small, fill=DIM)
        d.text((236, 54), label, font=big, fill=LABEL_COLOR[label])
        d.text((400, 62), f"c4/c2 {ch[4] / max(ch[2], 1):4.2f}  c0/c2 {ch[0] / max(ch[2], 1):4.2f}",
               font=small, fill=DIM)
        total = sum(ch) or 1
        for i, v in enumerate(ch):
            y = 104 + i * 32
            share = v / total
            d.text((236, y), f"c{i}", font=font, fill=FG)
            d.rectangle([272, y + 3, 272 + 380, y + 19], fill=(40, 43, 50))
            d.rectangle([272, y + 3, 272 + int(380 * min(share / 0.7, 1)), y + 19], fill=CH_COLOR[i])
            d.text((664, y), f"{share:4.2f}", font=font, fill=FG)
        d.text((W - 12, H - 12), "replay of data/macos27.2_mac16-8_run2.csv",
               font=small, fill=DIM, anchor="rd")
        frames.append(im)

frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=200, loop=0,
               optimize=True)
print("wrote", OUT, len(frames), "frames", os.path.getsize(OUT), "bytes")

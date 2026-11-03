---
name: My Mac's results
about: Share what the als sensor reports on your Mac
title: "Results: <model>, macOS <version>"
labels: results
---

**Model** (`sysctl -n hw.model`):

**macOS version** (`sw_vers -productVersion`):

**Report length** (printed by `als_probe.py`; 122 is the decoded layout):

**`python3 analyze.py out.csv` output:**

```
paste here
```

**What did `color_live.py` guess for each screen color?**

**Anything else** (light source used, phone model, IR remote test):

You can attach `out.csv`. It contains the sensor's timestamp, which reveals
your Mac's uptime; nothing else in it is known to be machine-specific.

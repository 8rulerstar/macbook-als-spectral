# Checks the decoder against the recorded runs and the README tables against
# analyze.py. Standard library only: python3 -m unittest -v test_decode

import csv, os, subprocess, sys, unittest

from als_decode import decode_report

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = ["data/macos27.0.1_mac16-8.csv", "data/macos27.2_mac16-8.csv",
        "data/macos27.2_mac16-8_run2.csv"]

# Channel shares from the README tables (step label prefix -> c0..c4).
README_TABLES = {
    RUNS[0]: {"blue": [0.58, 0.28, 0.06, 0.04, 0.03], "green": [0.08, 0.21, 0.40, 0.20, 0.10],
              "red": [0.15, 0.12, 0.17, 0.22, 0.34], "white": [0.24, 0.22, 0.25, 0.14, 0.15]},
    RUNS[1]: {"blue": [0.62, 0.27, 0.05, 0.03, 0.02], "green": [0.08, 0.20, 0.44, 0.21, 0.07],
              "red": [0.13, 0.10, 0.15, 0.21, 0.41], "white": [0.31, 0.21, 0.24, 0.13, 0.10]},
    RUNS[2]: {"blue": [0.64, 0.27, 0.05, 0.03, 0.02], "green": [0.10, 0.21, 0.43, 0.20, 0.06],
              "red": [0.10, 0.08, 0.13, 0.22, 0.47], "white": [0.34, 0.22, 0.23, 0.12, 0.08]},
}

def rows(path):
    with open(os.path.join(HERE, path), newline="") as f:
        return list(csv.DictReader(f))

class DecodeTest(unittest.TestCase):
    def test_recorded_reports_decode_to_logged_values(self):
        for path in RUNS:
            for r in rows(path):
                ch, lux = decode_report(bytes.fromhex(r["hex"]))
                self.assertEqual(ch, [int(r[f"c{i}"]) for i in range(5)], path)
                self.assertAlmostEqual(lux, float(r["lux"]), delta=0.06)

    def test_other_fields(self):
        from als_decode import decode_fields
        for path in RUNS:
            prev = None
            for r in rows(path):
                f = decode_fields(bytes.fromhex(r["hex"]))
                self.assertEqual(f["report_id"], 0xEC)
                self.assertEqual(f["const19"], 19)
                self.assertEqual(f["config"][0], f["config"][1])
                self.assertGreater(f["cct"], 1000)
                if prev:
                    self.assertGreater(f["seq"], prev["seq"])
                    self.assertGreater(f["timestamp_us"], prev["timestamp_us"])
                prev = f

    def test_other_lengths_are_not_decoded(self):
        report = bytes.fromhex(rows(RUNS[0])[0]["hex"])
        self.assertIsNone(decode_report(report[:121]))
        self.assertIsNone(decode_report(report + b"\x00" * 15))
        self.assertIsNone(decode_report(b""))

class ReadmeNumbersTest(unittest.TestCase):
    def test_analyze_output_matches_readme_tables(self):
        for path, table in README_TABLES.items():
            out = subprocess.run([sys.executable, "-B", os.path.join(HERE, "analyze.py"),
                                  os.path.join(HERE, path)],
                                 capture_output=True, text=True, check=True).stdout
            got = {}
            for line in out.splitlines()[1:]:
                parts = line.split()
                key = parts[0].lower()
                if key in table:
                    got[key] = [float(x) for x in parts[-6:-1]]
            self.assertEqual(got, table, path)

class ColorGuessTest(unittest.TestCase):
    # The thresholds in color_live.py were chosen on these same runs, so this
    # guards against regressions; it is not an independent accuracy test.
    EXPECT = {"baseline": "ROOM", "cover": "COVERED", "red": "RED", "green": "GREEN",
              "blue": "BLUE", "white": "WHITE", "flashlight": "WHITE"}

    def test_each_step_is_mostly_guessed_right(self):
        import statistics
        from color_live import guess
        for path in RUNS:
            steps = []
            for r in rows(path):
                key = r["phase"].lower().split()[0]
                if not steps or steps[-1][0] != key:
                    steps.append((key, []))
                steps[-1][1].append([float(r[f"c{i}"]) for i in range(5)])
            room = statistics.median(sum(x) for x in steps[0][1])
            for key, samples in steps:
                half = samples[len(samples) // 2:]
                right = sum(guess(x, room) == self.EXPECT[key] for x in half)
                self.assertGreaterEqual(right / len(half), 0.7, f"{path} {key}")

if __name__ == "__main__":
    unittest.main()

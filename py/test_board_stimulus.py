"""End-to-end test of py/board_stimulus.py: the integer model stands in for the board."""
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_stimulus as bs  # noqa: E402
from rtl_model import run_rtl_model  # noqa: E402


class TestBoardStimulus(unittest.TestCase):
    def test_make_writes_all_files(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(bs.main(["make", "--out", t, "--seconds", "2"]), 0)
            files = sorted(os.listdir(t))
            self.assertEqual(len(files), len(bs.SCENARIOS) * 2 * 2)
            a, fs = bs.read_wav(os.path.join(t, "stationary_noise_8k.wav"))
            self.assertEqual(fs, 8000)
            self.assertEqual(len(a), int((bs.LEAD_S + bs.TONE_S + 2) * 8000))

    def test_analyze_recovers_model_nr(self):
        secs = 4.0
        x, d = bs.build("stationary", secs, 1, noise_only=True)
        q = lambda v: [int(round(s * 2047)) for s in np.clip(v, -1, 2047 / 2048)]
        e = np.array(run_rtl_model(2, q(x), q(d), W=12, L=32, K=3, EPS_EXP=2)["e"]) / 2048.0
        dq = np.array(q(d)) / 2048.0
        n = len(e); lo = int(0.75 * n)
        expected = 10 * np.log10(np.mean(dq[lo:] ** 2) / np.mean(e[lo:] ** 2))
        h = bs.header(8000)
        pad = np.zeros(1234)                   # recordings start at different offsets
        with tempfile.TemporaryDirectory() as t:
            pb, pa = os.path.join(t, "b.wav"), os.path.join(t, "a.wav")
            rec_b = np.concatenate([h, dq]); rec_a = np.concatenate([pad, h, e])
            bs.write_wav(pb, rec_b, rec_b, 8000)
            bs.write_wav(pa, rec_a, rec_a, 8000)
            nr, _, _ = bs.nr_final(bs.read_wav(pb)[0], bs.read_wav(pa)[0], 8000, secs)
        self.assertGreater(expected, 15.0)
        self.assertAlmostEqual(nr, expected, delta=0.3)


if __name__ == "__main__":
    unittest.main()

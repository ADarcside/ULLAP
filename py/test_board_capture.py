"""Tests for py/check_board_capture.py using synthetic Signal Tap exports built from the integer model."""
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_board_capture as cbc  # noqa: E402
from rtl_model import run_rtl_model  # noqa: E402


def make_stimulus(n=1500, W=12, seed=3):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n) * 0.25
    d = np.convolve(x, [0.6, -0.3, 0.15, 0.05])[:n] + 0.02 * rng.standard_normal(n)
    q = lambda a: [int(v) for v in np.clip(np.round(a * (1 << (W - 1))), -(1 << (W - 1)), (1 << (W - 1)) - 1)]
    return q(x), q(d)


def write_capture(path, xs, ds, es, W=12, with_valid=False, radix="hex"):
    fmt = (lambda v: f"{v & ((1 << W) - 1):03X}") if radix == "hex" else str
    with open(path, "w") as f:
        f.write("Signal Tap export,anc_de2_115\n\n")           # preamble lines like Quartus writes
        cols = ["time unit: ns", "x_reg[11..0]", "d_reg[11..0]", "u_anc_core|e_out[11..0]"]
        if with_valid:
            cols.append("u_anc_core|out_valid")
        f.write(",".join(cols) + "\n")
        t = 0
        for x, d, e in zip(xs, ds, es):
            if with_valid:                                    # an idle row the parser must skip
                f.write(f"{t},{fmt(x)},{fmt(d)},{fmt(0)},0\n"); t += 20
            row = [str(t), fmt(x), fmt(d), fmt(e)] + (["1"] if with_valid else [])
            f.write(",".join(row) + "\n"); t += 20


class TestBoardCapture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, algo, corrupt=None, **kw):
        p = cbc.DEFAULTS[algo]
        xs, ds = make_stimulus()
        es = list(run_rtl_model(algo, xs, ds, W=12, L=32, **p)["e"])
        if corrupt is not None:
            es[corrupt] += 1
        path = os.path.join(self.tmp.name, "cap.csv")
        write_capture(path, xs, ds, es, **kw)
        return cbc.main(["--csv", path, "--algo", str(algo)] + (["--radix", kw["radix"]] if "radix" in kw else []))

    def test_exact_capture_passes_all_algorithms(self):
        for algo in (0, 1, 2):
            self.assertEqual(self._run(algo), 0)

    def test_single_wrong_sample_fails(self):
        self.assertEqual(self._run(2, corrupt=1234), 1)

    def test_valid_column_filters_idle_rows(self):
        self.assertEqual(self._run(2, with_valid=True), 0)

    def test_decimal_radix(self):
        self.assertEqual(self._run(1, radix="dec"), 0)

    def test_too_short_capture_fails(self):
        xs, ds = make_stimulus(n=200)
        es = run_rtl_model(2, xs, ds, W=12, L=32, **cbc.DEFAULTS[2])["e"]
        path = os.path.join(self.tmp.name, "short.csv")
        write_capture(path, xs, ds, es)
        self.assertEqual(cbc.main(["--csv", path, "--algo", "2"]), 1)

    def test_model_matches_rtl_golden_vectors(self):
        # Ties the checker's model to the RTL regression vectors (tb/manifest.txt, board settings).
        from fixedpoint import read_vec
        root = os.path.dirname(os.path.dirname(os.path.abspath(cbc.__file__)))
        for name in ("shift_e2_k3_W12_stationary", "shift_e2_k3_W12_path_switch"):
            rows, _ = read_vec(os.path.join(root, "vectors", "rtl", name), 12)
            x, d, e = [list(map(int, rows[:, i])) for i in (0, 1, 3)]
            bad, _ = cbc.compare(x, d, e, 2, 12, 32, MU_INT=512, K=3, EPS_EXP=2, ACC_W=29)
            self.assertEqual(bad, [], name)

if __name__ == "__main__":
    unittest.main()

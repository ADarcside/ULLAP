"""Simulator-free RTL cross-checks:  python -m unittest discover -s py -p 'test_rtl_model.py' -v
Checks the width-accurate model (py/rtl_model.py) of rtl/anc_core.v against run_fixed and against every
vector set listed in tb/manifest.txt (this also validates the manifest's MU_INT/K/ACC_W parameters).
This is NOT a Verilog simulation; see docs/verification.md."""
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import fixedpoint as fp
from fixedpoint import FxCfg, run_fixed
from rtl_model import run_rtl_model, upd_rtl

IDS = {"lms": 0, "nlms": 1, "nlms_shift": 2}


def rand_case(seed, n, W, amp):
    r = np.random.default_rng(seed)
    x = np.clip(r.standard_normal(n) * amp, -0.999, 0.999)
    d = np.clip(r.standard_normal(n) * 0.4, -0.999, 0.999)
    return x, d


def compare(algo, W, L, mu, MU_INT, K, n=500, amp=0.45, acc_bits=None, seed=3, rtl_fix=True):
    x, d = rand_case(seed, n, W, amp)
    q = run_fixed(algo, x, d, L, mu, FxCfg(W=W, acc_bits=acc_bits))
    I = q["ints"]
    m = run_rtl_model(IDS[algo], I["x"].tolist(), I["d"].tolist(), W, L, MU_INT, K, acc_bits, rtl_fix=rtl_fix)
    return m["y"] == I["y"].tolist() and m["e"] == I["e"].tolist() and m["w"] == I["W"][-1].tolist()


class T(unittest.TestCase):
    def test_model_matches_run_fixed(self):
        for algo, W, L, mu, mi, K in (("lms", 8, 16, 0.5, 512, 4), ("lms", 11, 2, 1.0, 1024, 4),
                                      ("nlms", 12, 8, 0.05, 51, 4), ("nlms", 11, 5, 0.1, 102, 4),
                                      ("nlms_shift", 11, 32, 2 ** -4, 512, 4), ("nlms_shift", 16, 7, 2 ** -3, 512, 3)):
            self.assertTrue(compare(algo, W, L, mu, mi, K), (algo, W, L))

    def test_model_matches_with_saturation(self):
        self.assertTrue(compare("lms", 11, 32, 2.0, 2048, 4, amp=1.0))                  # w/e/y saturate
        self.assertTrue(compare("lms", 11, 32, 0.5, 512, 4, acc_bits=18, amp=0.6))      # acc saturates
        self.assertTrue(compare("nlms_shift", 11, 32, 0.0625, 512, 4, acc_bits=18, amp=0.6))

    def test_large_k_update_rounding(self):
        """Regression for the S_UPD t_half overflow (ALGO 2, small MU_INT => narrow product, K >= 10, W = 8)."""
        for K in (10, 11, 12):
            self.assertFalse(compare("nlms_shift", 8, 32, 2.0 ** -K, 0, K, rtl_fix=False), K)   # old RTL behaviour
            self.assertTrue(compare("nlms_shift", 8, 32, 2.0 ** -K, 0, K, rtl_fix=True), K)     # fixed RTL / Python

    def test_update_guard_boundary(self):
        """upd_rtl (with the S_UPD guard) == ideal rs() for every shift around PRW and extreme/small products."""
        for PRW in (20, 27, 29, 40):
            lim = 1 << (PRW - 1)
            for s in range(-3, PRW + 6):
                for prod in (-lim, -lim + 1, -(lim >> 1), -3, -1, 0, 1, 3, (lim >> 1), lim - 1):
                    ideal = prod << (-s) if s <= 0 else (prod + (1 << (s - 1))) >> s
                    self.assertEqual(upd_rtl(prod, s, PRW, True), ideal, (PRW, s, prod))
        # pre-fix behaviour (ideal result is 0 in all three cases)
        self.assertEqual(upd_rtl(1, 28, 27, False), -1)        # s = PRW+1: half lands on the sign bit, positive product -> -1
        self.assertEqual(upd_rtl(-1, 29, 27, False), -1)       # s > PRW+1: half shifts out to 0, negative product -> -1
        self.assertEqual(upd_rtl(-1, 28, 27, False), 0)        # s = PRW+1, negative product: wraps back, happens to be right

    def test_arithmetic_rounding_edges(self):
        """Positive and negative arithmetic rounding (round-half-up, ties to +inf)."""
        # rs(v, s) tests with s = 1 (half-LSB = 1)
        self.assertEqual(fp.rs(0, 1), 0)
        self.assertEqual(fp.rs(1, 1), 1)      # +0.5 -> +1
        self.assertEqual(fp.rs(-1, 1), 0)     # -0.5 -> 0 (ties towards +inf)
        self.assertEqual(fp.rs(2, 1), 1)      # +1.0 -> +1
        self.assertEqual(fp.rs(-2, 1), -1)    # -1.0 -> -1
        self.assertEqual(fp.rs(3, 1), 2)      # +1.5 -> +2
        self.assertEqual(fp.rs(-3, 1), -1)    # -1.5 -> -1
        # s = 2 (half-LSB = 2)
        self.assertEqual(fp.rs(2, 2), 1)      # +0.5 -> +1
        self.assertEqual(fp.rs(-2, 2), 0)     # -0.5 -> 0
        self.assertEqual(fp.rs(6, 2), 2)      # +1.5 -> +2
        self.assertEqual(fp.rs(-6, 2), -1)    # -1.5 -> -1
        # non-positive shifts (left shift)
        self.assertEqual(fp.rs(5, 0), 5)
        self.assertEqual(fp.rs(5, -1), 10)
        self.assertEqual(fp.rs(-5, -2), -20)
        # upd_rtl with positive and negative products
        PRW = 24
        self.assertEqual(upd_rtl(1, 1, PRW), 1)
        self.assertEqual(upd_rtl(-1, 1, PRW), 0)
        self.assertEqual(upd_rtl(3, 1, PRW), 2)
        self.assertEqual(upd_rtl(-3, 1, PRW), -1)

    def test_parameter_extremes(self):
        """Cross-check model against fixed-point reference across parameter boundaries."""
        # Minimum filter length L=2 across all algorithms
        self.assertTrue(compare("lms", 11, 2, 0.5, 512, 4))
        self.assertTrue(compare("nlms", 11, 2, 0.1, 102, 4))
        self.assertTrue(compare("nlms_shift", 11, 2, 0.0625, 512, 4))
        # Minimum legal K for NLMS-shift
        self.assertTrue(compare("nlms_shift", 11, 32, 1.0, 512, 0))    # W=11, F=10 -> K_min=0
        self.assertTrue(compare("nlms_shift", 8, 16, 0.125, 512, 3))    # W=8, F=7  -> K_min=3
        # Boundary word widths W=28, 30, 31 and accumulators
        self.assertTrue(compare("lms", 28, 32, 0.5, 512, 4, acc_bits=61))
        self.assertTrue(compare("nlms_shift", 28, 32, 0.0625, 512, 4, acc_bits=61))
        self.assertTrue(compare("lms", 30, 2, 0.5, 512, 4, acc_bits=61))
        self.assertTrue(compare("lms", 31, 2, 0.5, 512, 4, acc_bits=62))
        self.assertTrue(compare("lms", 11, 32, 0.5, 512, 4, acc_bits=62))
        self.assertTrue(compare("lms", 11, 32, 0.5, 512, 4, acc_bits=11))

    def test_dot_product_large_w_overflow(self):
        """Regression: w @ xv and xv @ xv wrap in int64 if computed via NumPy, but exact integer sum avoids it."""
        W = 31
        L = 32
        WMIN = -(1 << (W - 1))
        xv = np.full(L, WMIN, dtype=np.int64)
        w = np.full(L, WMIN, dtype=np.int64)

        # 1. Demonstrate that NumPy's int64 dot product wraps to 0 due to 2^65 % 2^64 == 0:
        np_dot = int(w @ xv)
        self.assertEqual(np_dot, 0)
        exact_dot = sum(int(a) * int(b) for a, b in zip(w, xv))
        self.assertEqual(exact_dot, 1 << 65)

        # 2. Check that run_fixed with near-rail stimulus matches rtl_model bit-identically:
        cfg = fp.FxCfg(W=W, acc_bits=62)
        x_rail = np.full(40, -0.999)
        d_rail = np.full(40, -0.999)

        q_shift = fp.run_fixed("nlms_shift", x_rail, d_rail, L, 0.0625, cfg)
        I_shift = q_shift["ints"]
        m_shift = run_rtl_model(2, I_shift["x"].tolist(), I_shift["d"].tolist(), W, L, 512, 4, 62)
        self.assertEqual(m_shift["y"], I_shift["y"].tolist())
        self.assertEqual(m_shift["e"], I_shift["e"].tolist())
        self.assertEqual(m_shift["w"], I_shift["W"][-1].tolist())

        q_lms = fp.run_fixed("lms", x_rail, d_rail, L, 0.5, cfg)
        I_lms = q_lms["ints"]
        m_lms = run_rtl_model(0, I_lms["x"].tolist(), I_lms["d"].tolist(), W, L, 512, 4, 62)
        self.assertEqual(m_lms["y"], I_lms["y"].tolist())
        self.assertEqual(m_lms["e"], I_lms["e"].tolist())
        self.assertEqual(m_lms["w"], I_lms["W"][-1].tolist())

    def test_manifest_vectors(self):
        with open(os.path.join(ROOT, "tb", "manifest.txt")) as f:
            lines = [l.split() for l in f if l.strip() and l[0] != "#"]
        self.assertEqual(len(lines), 53)
        for name, algo, W, L, mi, K, accw, prefix, n, eps in lines:
            algo, W, L, mi, K, accw, n, eps = map(int, (algo, W, L, mi, K, accw, n, eps))
            rows, w = fp.read_vec(os.path.join(ROOT, prefix), W)
            self.assertEqual(len(rows), n, name)
            m = run_rtl_model(algo, rows[:, 0].tolist(), rows[:, 1].tolist(), W, L, mi, K, accw, EPS_EXP=eps)
            self.assertEqual(m["y"], rows[:, 2].tolist(), name)
            self.assertEqual(m["e"], rows[:, 3].tolist(), name)
            self.assertEqual(m["w"], w.tolist(), name)
            fp_flg = os.path.join(ROOT, prefix + ".flg")
            flg = 0
            if os.path.exists(fp_flg):
                with open(fp_flg) as fh:
                    flg = int(fh.read(), 16)
            got = sum(1 << b for b, k in ((1, "acc"), (2, "y"), (3, "e"), (4, "g"), (5, "w")) if m["flags"][k])
            self.assertEqual(got, flg & 0x3E, name)


if __name__ == "__main__":
    unittest.main()

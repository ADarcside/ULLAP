"""Unit tests for adaptation freeze semantics in run_fixed and run_rtl_model."""
import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fixedpoint import FxCfg, run_fixed
from rtl_model import run_rtl_model
from signals import make_scenario


class TestAdaptationFreeze(unittest.TestCase):
    def setUp(self):
        sc = make_scenario("stationary", 1500, seed=42)
        self.x = sc.x[:1500]
        self.d = sc.d[:1500]
        self.n = len(self.x)

    def test_all_zero_mask_equals_unmasked(self):
        """(a) all-zero mask equals unmasked, bit-exact across LMS, NLMS, and NLMS-Shift."""
        zero_mask = np.zeros(self.n, dtype=int)
        cases = [
            ("lms", 0, 12, 32, 0.5, 512, 4, 10),
            ("nlms", 1, 12, 32, 0.05, 51, 4, 10),
            ("nlms_shift", 2, 12, 32, 0.125, 512, 3, 2),
        ]
        for name, algo_id, W, L, mu, mi, K, eps in cases:
            cfg = FxCfg(W=W, eps_exp=eps)
            # 1. run_fixed
            r_unmasked = run_fixed(name, self.x, self.d, L, mu, cfg, freeze=None)
            r_zero = run_fixed(name, self.x, self.d, L, mu, cfg, freeze=zero_mask)
            self.assertTrue(np.array_equal(r_unmasked["ints"]["y"], r_zero["ints"]["y"]), f"{name} y mismatch")
            self.assertTrue(np.array_equal(r_unmasked["ints"]["e"], r_zero["ints"]["e"]), f"{name} e mismatch")
            self.assertTrue(np.array_equal(r_unmasked["ints"]["W"], r_zero["ints"]["W"]), f"{name} W mismatch")
            self.assertEqual(r_unmasked["counts"], r_zero["counts"], f"{name} counts mismatch")

            # 2. run_rtl_model
            xi = r_unmasked["ints"]["x"].tolist()
            di = r_unmasked["ints"]["d"].tolist()
            m_unmasked = run_rtl_model(algo_id, xi, di, W, L, mi, K, EPS_EXP=eps, freeze=None)
            m_zero = run_rtl_model(algo_id, xi, di, W, L, mi, K, EPS_EXP=eps, freeze=zero_mask)
            self.assertEqual(m_unmasked["y"], m_zero["y"], f"{name} rtl_model y mismatch")
            self.assertEqual(m_unmasked["e"], m_zero["e"], f"{name} rtl_model e mismatch")
            self.assertEqual(m_unmasked["w"], m_zero["w"], f"{name} rtl_model w mismatch")
            self.assertEqual(m_unmasked["flags"], m_zero["flags"], f"{name} rtl_model flags mismatch")

    def test_all_one_mask_leaves_weights_unchanged(self):
        """(b) all-one mask leaves weights unchanged (initial zeros stay zeros)."""
        one_mask = np.ones(self.n, dtype=int)
        cases = [
            ("lms", 0, 12, 32, 0.5, 512, 4, 10),
            ("nlms", 1, 12, 32, 0.05, 51, 4, 10),
            ("nlms_shift", 2, 12, 32, 0.125, 512, 3, 2),
        ]
        for name, algo_id, W, L, mu, mi, K, eps in cases:
            cfg = FxCfg(W=W, eps_exp=eps)
            r = run_fixed(name, self.x, self.d, L, mu, cfg, freeze=one_mask)
            # Weights must remain all zeros
            self.assertTrue(np.all(r["ints"]["W"] == 0), f"{name} weights not zero")
            self.assertEqual(r["counts"]["w"], 0, f"{name} w saturation count not 0")
            # Filter output y should be 0 because weights are 0, so e = d
            self.assertTrue(np.all(r["ints"]["y"] == 0), f"{name} y not zero")
            self.assertTrue(np.array_equal(r["ints"]["e"], r["ints"]["d"]), f"{name} e != d")

            # run_rtl_model
            xi = r["ints"]["x"].tolist()
            di = r["ints"]["d"].tolist()
            m = run_rtl_model(algo_id, xi, di, W, L, mi, K, EPS_EXP=eps, freeze=one_mask)
            self.assertTrue(all(w == 0 for w in m["w"]), f"{name} rtl_model weights not zero")
            self.assertEqual(m["flags"]["w"], 0, f"{name} rtl_model w flag set")
            self.assertEqual(m["y"], [0] * self.n, f"{name} rtl_model y not zero")
            self.assertEqual(m["e"], di, f"{name} rtl_model e != d")

    def test_mid_run_toggle(self):
        """(c) mid-run toggle: weights identical at both ends of the frozen segment while e keeps changing."""
        # 500 free / 500 frozen / 500 free
        frz_mask = np.zeros(self.n, dtype=int)
        frz_mask[500:1000] = 1

        cases = [
            ("lms", 0, 12, 32, 0.5, 512, 4, 10),
            ("nlms", 1, 12, 32, 0.05, 51, 4, 10),
            ("nlms_shift", 2, 12, 32, 0.125, 512, 3, 2),
        ]
        for name, algo_id, W, L, mu, mi, K, eps in cases:
            cfg = FxCfg(W=W, eps_exp=eps)
            r = run_fixed(name, self.x, self.d, L, mu, cfg, freeze=frz_mask)
            W_hist = r["ints"]["W"]
            e_hist = r["ints"]["e"]

            # Weights must be identical across the entire frozen segment [500:1000]
            w_at_start = W_hist[499]
            for idx in range(500, 1000):
                self.assertTrue(np.array_equal(W_hist[idx], w_at_start),
                                f"{name} sample {idx} weight changed during freeze")
            # e must continue to change and not be all identical
            e_frozen_segment = e_hist[500:1000]
            self.assertGreater(len(np.unique(e_frozen_segment)), 1,
                               f"{name} e remained constant during freeze")

            # After unfreezing at 1000, weights must resume adapting
            self.assertFalse(np.array_equal(W_hist[1499], w_at_start),
                             f"{name} weights failed to resume adapting after freeze")

            # Check exact agreement with rtl_model
            xi = r["ints"]["x"].tolist()
            di = r["ints"]["d"].tolist()
            m = run_rtl_model(algo_id, xi, di, W, L, mi, K, EPS_EXP=eps, freeze=frz_mask)
            self.assertEqual(m["y"], r["ints"]["y"].tolist(), f"{name} rtl_model y mismatch")
            self.assertEqual(m["e"], r["ints"]["e"].tolist(), f"{name} rtl_model e mismatch")
            self.assertEqual(m["w"], r["ints"]["W"][-1].tolist(), f"{name} rtl_model w mismatch")


if __name__ == "__main__":
    unittest.main()
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

    def test_satall_two_phase(self):
        """(d) satall two-phase: phase 1 (0..N1-1) unfrozen has counts['w']==0;
        at index N1 the unfrozen update saturates a coefficient (sum < WMIN on coef 0);
        with freeze ON from index N1 onward, counts['w']==0 and final w == w[N1-1].
        Note on criterion (b): Saturation on either rail (sum < WMIN or sum > WMAX)
        satisfies the saturation requirement. On amp_steps xscale=0.25, coefficient 0
        saturates below WMIN (-2048) on sample N1 for all three algorithms.
        """
        sc = make_scenario("amp_steps", 16000, seed=1)
        configs = [
            ("lms", 0.5, 10, 4959, 1000),
            ("nlms", 0.05, 10, 377, 1000),
            ("nlms_shift", 0.125, 2, 6154, 1000),
        ]
        for name, mu, eps, N1, n_frz in configs:
            n_total = N1 + n_frz
            x = (sc.x * 0.25)[:n_total]
            d = sc.d[:n_total]
            cfg = FxCfg(W=12, eps_exp=eps)

            # Phase 1: samples 0..N1-1 (length N1)
            r_p1 = run_fixed(name, x[:N1], d[:N1], 32, mu, cfg, freeze=None)
            self.assertEqual(r_p1["counts"]["w"], 0, f"{name}: phase 1 counts['w'] != 0")

            # Unfrozen update at index N1 must take some coefficient above WMAX
            r_next = run_fixed(name, x[:N1+1], d[:N1+1], 32, mu, cfg, freeze=None)
            self.assertGreater(r_next["counts"]["w"], 0, f"{name}: unfrozen update at index N1 did not saturate w")

            # Frozen run: samples N1..n_total-1 frozen
            frz_mask = np.zeros(n_total, dtype=int)
            frz_mask[N1:] = 1
            r_frz = run_fixed(name, x, d, 32, mu, cfg, freeze=frz_mask)
            self.assertEqual(r_frz["counts"]["w"], 0, f"{name}: frozen run counts['w'] != 0")

            # Unfrozen full run must give counts['w'] > 0
            r_unfrz_full = run_fixed(name, x, d, 32, mu, cfg, freeze=None)
            self.assertGreater(r_unfrz_full["counts"]["w"], 0, f"{name}: unfrozen full run counts['w'] == 0")

            # Final w must match w at end of phase 1
            w_p1 = r_p1["ints"]["W"][-1]
            w_frz = r_frz["ints"]["W"][-1]
            self.assertTrue(np.array_equal(w_frz, w_p1), f"{name}: frozen final w != w at N1")
            self.assertFalse(np.all(w_p1 == 0), f"{name}: w at N1 is all zero")

            max_w_N1 = np.max(np.abs(r_p1["W"][-1]))
            print(f"satall assert passed: {name:10s} N1={N1:4d}, first-sat sample={N1+1:4d}, max|w|={max_w_N1:.6f}")

    def test_freeze_early_discrimination(self):
        """(e) freeze_early: freezing samples 15..18 on amp_steps xscale=0.25
        causes measurable difference in e, y, and final w for all three algorithms."""
        sc = make_scenario("amp_steps", 16000, seed=1)
        n = 1000
        x = (sc.x * 0.25)[:n]
        d = sc.d[:n]
        frz_early = np.zeros(n, dtype=int)
        frz_early[15:19] = 1

        configs = [
            ("lms", 0.5, 10),
            ("nlms", 0.05, 10),
            ("nlms_shift", 0.125, 2),
        ]
        for name, mu, eps in configs:
            cfg = FxCfg(W=12, eps_exp=eps)
            r_unfrz = run_fixed(name, x, d, 32, mu, cfg, freeze=None)
            r_frz = run_fixed(name, x, d, 32, mu, cfg, freeze=frz_early)

            diff_e = np.max(np.abs(r_unfrz["e"] - r_frz["e"]))
            diff_y = np.max(np.abs(r_unfrz["y"] - r_frz["y"]))
            diff_w = np.max(np.abs(r_unfrz["W"][-1] - r_frz["W"][-1]))

            self.assertGreater(diff_e, 0, f"{name}: diff_e is 0")
            self.assertGreater(diff_y, 0, f"{name}: diff_y is 0")
            self.assertGreater(diff_w, 0, f"{name}: diff_w is 0")
            print(f"freeze_early assert passed: {name:10s} max|e| diff={diff_e:.6f}, max|y| diff={diff_y:.6f}, max|w| diff={diff_w:.6f}")

    def test_freeze_hold_patterns(self):
        """(f) freeze_hold: 4 per-sample patterns A (frozen), B (unfrz), C (unfrz), D (frozen).
        Checks that weights adapt on B and C, remain held on A and D, and match run_rtl_model."""
        sc = make_scenario("amp_steps", 1000, seed=1)
        n = 200
        x = (sc.x * 0.25)[:n]
        d = sc.d[:n]
        frz_mask = np.array([1 if (i % 4 in (0, 3)) else 0 for i in range(n)], dtype=int)

        cases = [
            ("lms", 0, 12, 32, 0.5, 512, 4, 10),
            ("nlms", 1, 12, 32, 0.05, 51, 4, 10),
            ("nlms_shift", 2, 12, 32, 0.125, 512, 3, 2),
        ]
        for name, algo_id, W, L, mu, mi, K, eps in cases:
            cfg = FxCfg(W=W, eps_exp=eps)
            r_unfrz = run_fixed(name, x, d, L, mu, cfg, freeze=None)
            r_frz = run_fixed(name, x, d, L, mu, cfg, freeze=frz_mask)

            # Check that adaptation occurred (non-zero weights)
            max_w = np.max(np.abs(r_frz["ints"]["W"][-1]))
            self.assertGreater(max_w, 0, f"{name}: weights are all zero")

            # Check that freeze had effect (differs from unfrozen)
            diff_w = np.max(np.abs(r_unfrz["ints"]["W"][-1] - r_frz["ints"]["W"][-1]))
            self.assertGreater(diff_w, 0, f"{name}: weights did not differ from unfrozen")

            # Bit-exact check against run_rtl_model
            xi = r_frz["ints"]["x"].tolist()
            di = r_frz["ints"]["d"].tolist()
            m = run_rtl_model(algo_id, xi, di, W, L, mi, K, EPS_EXP=eps, freeze=frz_mask)
            self.assertEqual(m["y"], r_frz["ints"]["y"].tolist(), f"{name}: rtl_model y mismatch")
            self.assertEqual(m["e"], r_frz["ints"]["e"].tolist(), f"{name}: rtl_model e mismatch")
            self.assertEqual(m["w"], r_frz["ints"]["W"][-1].tolist(), f"{name}: rtl_model w mismatch")
            print(f"freeze_hold assert passed: {name:10s} max|w|={max_w}, diff_vs_unfrz={diff_w}")


if __name__ == "__main__":
    unittest.main()
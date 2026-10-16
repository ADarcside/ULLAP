"""Unit tests (stdlib unittest):  python -m unittest discover -s py -v"""
import math
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixedpoint as fp
from algos import run_float, EPS
from fixedpoint import FxCfg, run_fixed
from metrics import evaluate
from signals import make_scenario, make_paths, Scenario

N, L = 4000, 32


class T(unittest.TestCase):
    def test_rounding_and_saturation(self):
        self.assertEqual(fp.rs(5, 1, "nearest"), 3)
        self.assertEqual(fp.rs(-5, 1, "nearest"), -2)
        self.assertEqual(fp.rs(5, 1, "floor"), 2)
        self.assertEqual(fp.rs(3, -2), 12)
        self.assertEqual(fp.sat(200, 8), (127, 1))
        self.assertEqual(fp.sat(-129, 8), (-128, 1))
        v, c = fp.sat(np.array([0, 300, -300, 5]), 8)
        self.assertEqual((v.tolist(), c), ([0, 127, -128, 5], 2))

    def test_scenarios_deterministic_and_in_range(self):
        for name in ("stationary", "amp_steps", "path_switch"):
            a, b = make_scenario(name, N, 1), make_scenario(name, N, 1)
            self.assertTrue(np.array_equal(a.d, b.d))
            self.assertEqual(a.n_clip, 0)
            self.assertLess(np.abs(a.d).max(), 1.0)
        self.assertEqual(make_scenario("amp_steps", 1000, 1).events, [350, 600])

    def test_float_identifies_known_fir(self):
        h = make_paths()[0]
        x = 0.2 * np.random.default_rng(0).standard_normal(N)
        x = np.convolve(x, [1, .8, .6, .4, .2])[:N]
        d = np.convolve(x, h)[:N]
        w = run_float("nlms", x, d, L, 0.5)["W"][-1]
        err = 10 * math.log10(np.sum((w[:16] - h) ** 2) + np.sum(w[16:] ** 2))
        self.assertLess(err, -40)

    def test_all_algos_cancel_stationary_noise(self):
        sc = make_scenario("stationary", N, 1)
        for algo, mu in (("lms", 1.0), ("nlms", 0.1), ("nlms_shift", 0.125)):
            r = run_float(algo, sc.x, sc.d, L, mu)
            self.assertGreater(evaluate(sc, r["e"], r["W"], L)["nr_final"], 6, algo)

    def test_shift_normaliser_within_factor_two(self):
        for P in np.geomspace(1e-3, 50, 200):
            self.assertTrue(0.5 <= (P + EPS) * 2.0 ** -math.frexp(P + EPS)[1] < 1.0)

    def test_fixed24_tracks_float_without_overflow(self):
        sc = make_scenario("stationary", N, 1)
        for algo, mu in (("lms", 1.0), ("nlms", 0.1), ("nlms_shift", 0.125)):
            f = run_float(algo, sc.x, sc.d, L, mu)
            q = run_fixed(algo, sc.x, sc.d, L, mu, FxCfg(W=24))
            nf, nq = (evaluate(sc, r["e"], r["W"], L)["nr_final"] for r in (f, q))
            self.assertLess(abs(nf - nq), 1.0, algo)
            self.assertEqual(sum(q["counts"].values()), 0, algo)

    def test_overflow_counters_fire(self):
        sc = make_scenario("stationary", 600, 1)
        q = run_fixed("nlms", 8 * sc.x, sc.d, L, 0.3, FxCfg(W=12))        # reference out of range
        self.assertGreater(q["counts"]["in_x"], 0)
        q = run_fixed("lms", sc.x, sc.d, L, 2.0, FxCfg(W=12, acc_bits=12))  # far too narrow accumulator
        self.assertGreater(q["counts"]["acc"], 0)

    def test_vector_roundtrip(self):
        sc = make_scenario("stationary", 300, 1)
        q = run_fixed("nlms_shift", sc.x, sc.d, L, 0.25, FxCfg(W=13))
        with tempfile.TemporaryDirectory() as t:
            fp.write_vec(os.path.join(t, "v"), q, 200)
            rows, w = fp.read_vec(os.path.join(t, "v"), 13)
        I = q["ints"]
        self.assertTrue(np.array_equal(rows, np.stack([I["x"][:200], I["d"][:200], I["y"][:200], I["e"][:200]], 1)))
        self.assertTrue(np.array_equal(w, I["W"][199]))

    def test_metrics_settling_time(self):
        n, r = 8000, np.random.default_rng(0)
        nz = 0.1 * r.standard_normal(n)
        h = np.array([.5, .5, .5, .5])
        t = np.arange(n)[:, None]
        W = h * (1 - np.exp(-t / 500.0)) + 0.03 * np.array([1, -1, 1, -1])   # tau=500 samples + fixed floor
        sc = Scenario("fake", nz, nz.copy(), np.zeros(n), [4000], [(0, h)])
        m = evaluate(sc, nz * (0.01 + np.exp(-np.arange(n) / 500)), W, 4)
        self.assertTrue(100 < m["settle_ms"] < 800, m["settle_ms"])   # ~ 1600 samples = 200 ms expected
        self.assertGreater(m["nr_final"], 30)
        self.assertLess(m["coef_db"], -20)
        self.assertEqual(m["track_ms"], 0.0)       # nothing changes at the event -> zero tracking time


if __name__ == "__main__":
    unittest.main()

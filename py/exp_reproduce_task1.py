"""TASK 1: Reproducibility of amp_steps and operating point audit."""
import os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "py"))

from signals import make_scenario, SCENARIOS
from fixedpoint import FxCfg, run_fixed
from metrics import evaluate
from algos import shift_k, run_float

WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
L = 32
W = 12

def run_task1():
    print("=" * 90)
    print("TASK 1: REPRODUCIBILITY OF AMP_STEPS AND OPERATING POINT INVESTIGATION")
    print("=" * 90)

    configs_to_test = [
        ("K=3, eps_exp=2 (mu=2^-3=0.125)", 0.125, FxCfg(W=12, eps_exp=2)),
        ("K=4, eps_exp=2 (mu=2^-4=0.0625)", 0.0625, FxCfg(W=12, eps_exp=2)),
        ("K=3, eps_exp=10 (mu=2^-3=0.125, baseline eps)", 0.125, FxCfg(W=12, eps_exp=10)),
        ("K=4, eps_exp=10 (mu=2^-4=0.0625, baseline eps)", 0.0625, FxCfg(W=12, eps_exp=10)),
        ("Float K=3, eps=2^-2", 0.125, "float_eps2"),
        ("Float K=4, eps=2^-2", 0.0625, "float_eps2"),
        ("Float K=4, eps=2^-10 (run_float default)", 0.0625, "float_eps10"),
    ]

    scenarios = ["stationary", "amp_steps", "path_switch", "wav"]
    seeds = [1, 2, 3]

    for title, mu_in, cfg in configs_to_test:
        print(f"\n--- Testing: {title} ---")
        for sc_name in scenarios:
            fin_nrs, all_nrs = [], []
            for seed in seeds:
                sc = make_scenario(sc_name, 16000, seed, WAV if sc_name == "wav" else None)
                if isinstance(cfg, str):
                    eps_val = 2.0 ** -2 if cfg == "float_eps2" else 2.0 ** -10
                    res = run_float("nlms_shift", sc.x, sc.d, L, mu_in, eps=eps_val)
                    m = evaluate(sc, res["e"], res["W"], L)
                else:
                    res = run_fixed("nlms_shift", sc.x, sc.d, L, mu_in, cfg)
                    m = evaluate(sc, res["e"], res["W"], L)
                fin_nrs.append(m["nr_final"])
                all_nrs.append(m["nr_all"])
            print(f"  {sc_name:12}: Final NR: {fin_nrs[0]:.2f}, {fin_nrs[1]:.2f}, {fin_nrs[2]:.2f} (mean: {np.mean(fin_nrs):.2f} dB) | Whole-run NR: {all_nrs[0]:.2f}, {all_nrs[1]:.2f}, {all_nrs[2]:.2f} (mean: {np.mean(all_nrs):.2f} dB)")

if __name__ == "__main__":
    run_task1()

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

print("==========================================================================================")
print("TASK 1: REPRODUCIBILITY OF AMP_STEPS AND OPERATING POINT INVESTIGATION")
print("==========================================================================================")

# Let's test different combinations of mu, K, eps_exp to see what produced each number:
configs_to_test = [
    ("K=3, eps_exp=2 (mu=2^-3=0.125)", 0.125, FxCfg(W=12, eps_exp=2)),
    ("K=4, eps_exp=2 (mu=2^-4=0.0625)", 0.0625, FxCfg(W=12, eps_exp=2)),
    ("K=3, eps_exp=10 (mu=2^-3=0.125, baseline eps)", 0.125, FxCfg(W=12, eps_exp=10)),
    ("K=4, eps_exp=10 (mu=2^-4=0.0625, baseline eps)", 0.0625, FxCfg(W=12, eps_exp=10)),
    ("Float K=3, eps=2^-2", 0.125, "float_eps2"),
    ("Float K=4, eps=2^-2", 0.0625, "float_eps2"),
    ("Float K=4, eps=2^-10 (run_float default)", 0.0625, "float_eps10"),
]

for label, mu_val, cfg in configs_to_test:
    k_calc = shift_k(mu_val)
    print(f"\n--- Testing: {label} ---")
    print(f"mu passed: {mu_val}, shift_k(mu): {k_calc}, cfg: {cfg}")
    
    for sc_name in ["stationary", "amp_steps", "path_switch", "wav"]:
        nr_finals = []
        nr_alls = []
        for seed in [1, 2, 3]:
            sc = make_scenario(sc_name, 16000, seed, WAV if sc_name == "wav" else None)
            if isinstance(cfg, str):
                eps = 2.0**-2 if "eps2" in cfg else 2.0**-10
                r = run_float("nlms_shift", sc.x, sc.d, L, mu_val, eps=eps)
            else:
                r = run_fixed("nlms_shift", sc.x, sc.d, L, mu_val, cfg)
            m = evaluate(sc, r["e"], r["W"], L)
            nr_finals.append(m["nr_final"])
            nr_alls.append(m["nr_all"])
        print(f"  {sc_name:12}: Final NR: {nr_finals[0]:.2f}, {nr_finals[1]:.2f}, {nr_finals[2]:.2f} (mean: {np.mean(nr_finals):.2f} dB) | Whole-run NR: {nr_alls[0]:.2f}, {nr_alls[1]:.2f}, {nr_alls[2]:.2f} (mean: {np.mean(nr_alls):.2f} dB)")

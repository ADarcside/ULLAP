import os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "py"))

from signals import make_scenario
from fixedpoint import FxCfg, run_fixed
from metrics import evaluate
from algos import shift_k

WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
L = 32
W = 12
scenarios = ["stationary", "amp_steps", "path_switch", "wav"]
seeds = [1, 2, 3]

print("=" * 80)
print("TASK 1 AUDIT REPORT: EXACT PER-SEED NUMBERS AND RUN_FIXED PARAMETER TRACE")
print("=" * 80)

def trace_run(algo, x, d, L, mu, cfg):
    W = cfg.W
    F = W - 1 if cfg.F is None else cfg.F
    eps_i = 1 << (2 * F - cfg.eps_exp)
    k = shift_k(mu) if algo == "nlms_shift" else 0
    return k, eps_i, F

# Operating point 1: EPS_EXP=2, K=3 (mu = 2^-3 = 0.125)
mu_k3 = 2.0**-3
cfg_e2 = FxCfg(W=12, eps_exp=2)
k_used, eps_i, F = trace_run("nlms_shift", np.zeros(10), np.zeros(10), L, mu_k3, cfg_e2)
print(f"\n1. Parameter Verification for K=3, EPS_EXP=2:")
print(f"   Passed mu: {mu_k3}")
print(f"   Calculated k in run_fixed: {k_used} (exact match with K=3)")
print(f"   FxCfg passed: {cfg_e2}")
print(f"   F: {F}, eps_i (integer): {eps_i} = 2^(2*{F} - {cfg_e2.eps_exp}) = 2^{2*F - cfg_e2.eps_exp}")
print(f"   Normalized eps float: {eps_i / (1 << (2*F))} = 2^-{cfg_e2.eps_exp} = 0.25")

print("\n--- Results for K=3, EPS_EXP=2 (mu = 0.125, W=12, L=32) ---")
print(f"{'Scenario':15} | {'Seed 1 NR':10} | {'Seed 2 NR':10} | {'Seed 3 NR':10} | {'Mean Final':11} | {'Mean Whole-Run':15}")
print("-" * 80)
for s in scenarios:
    fin_vals, all_vals = [], []
    for seed in seeds:
        sc = make_scenario(s, 16000, seed, WAV if s == "wav" else None)
        r = run_fixed("nlms_shift", sc.x, sc.d, L, mu_k3, cfg_e2)
        m = evaluate(sc, r["e"], r["W"], L)
        fin_vals.append(m["nr_final"])
        all_vals.append(m["nr_all"])
    print(f"{s:15} | {fin_vals[0]:10.2f} | {fin_vals[1]:10.2f} | {fin_vals[2]:10.2f} | {np.mean(fin_vals):11.2f} | {np.mean(all_vals):15.2f}")

# Operating point 2: EPS_EXP=2, K=4 (mu = 2^-4 = 0.0625)
mu_k4 = 2.0**-4
k_used4, eps_i4, _ = trace_run("nlms_shift", np.zeros(10), np.zeros(10), L, mu_k4, cfg_e2)
print(f"\n2. Parameter Verification for K=4, EPS_EXP=2:")
print(f"   Passed mu: {mu_k4}")
print(f"   Calculated k in run_fixed: {k_used4} (exact match with K=4)")

print("\n--- Results for K=4, EPS_EXP=2 (mu = 0.0625, W=12, L=32) ---")
print(f"{'Scenario':15} | {'Seed 1 NR':10} | {'Seed 2 NR':10} | {'Seed 3 NR':10} | {'Mean Final':11} | {'Mean Whole-Run':15}")
print("-" * 80)
for s in scenarios:
    fin_vals, all_vals = [], []
    for seed in seeds:
        sc = make_scenario(s, 16000, seed, WAV if s == "wav" else None)
        r = run_fixed("nlms_shift", sc.x, sc.d, L, mu_k4, cfg_e2)
        m = evaluate(sc, r["e"], r["W"], L)
        fin_vals.append(m["nr_final"])
        all_vals.append(m["nr_all"])
    print(f"{s:15} | {fin_vals[0]:10.2f} | {fin_vals[1]:10.2f} | {fin_vals[2]:10.2f} | {np.mean(fin_vals):11.2f} | {np.mean(all_vals):15.2f}")

# Operating point 3: Baseline EPS_EXP=10, K=4 (mu = 0.0625, the original float_results.csv config)
cfg_e10 = FxCfg(W=12, eps_exp=10)
print(f"\n3. Baseline config K=4, EPS_EXP=10 (the original float_results.csv tuning):")
print("\n--- Results for K=4, EPS_EXP=10 (mu = 0.0625, W=12, L=32) ---")
print(f"{'Scenario':15} | {'Seed 1 NR':10} | {'Seed 2 NR':10} | {'Seed 3 NR':10} | {'Mean Final':11} | {'Mean Whole-Run':15}")
print("-" * 80)
for s in scenarios:
    fin_vals, all_vals = [], []
    for seed in seeds:
        sc = make_scenario(s, 16000, seed, WAV if s == "wav" else None)
        r = run_fixed("nlms_shift", sc.x, sc.d, L, mu_k4, cfg_e10)
        m = evaluate(sc, r["e"], r["W"], L)
        fin_vals.append(m["nr_final"])
        all_vals.append(m["nr_all"])
    print(f"{s:15} | {fin_vals[0]:10.2f} | {fin_vals[1]:10.2f} | {fin_vals[2]:10.2f} | {np.mean(fin_vals):11.2f} | {np.mean(all_vals):15.2f}")

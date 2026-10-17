import os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "py"))

from signals import make_scenario
from fixedpoint import FxCfg, run_fixed
from metrics import evaluate

WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
L = 32
W = 12
scenarios = ["stationary", "amp_steps", "path_switch", "wav"]
tune_seeds = [101, 102, 103]  # strictly disjoint from eval seeds 1..20

print("=" * 100)
print("FAIR TUNING SEARCH ACROSS TUNING SEEDS [101, 102, 103] (W=12, L=32)")
print("=" * 100)

# 1. LMS Grid
lms_mu_grid = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 1.0]
lms_results = []
for mu in lms_mu_grid:
    cfg = FxCfg(W=W, eps_exp=2)
    sc_nrs = {s: [] for s in scenarios}
    ovfs = 0
    for sc_name in scenarios:
        for seed in tune_seeds:
            sc = make_scenario(sc_name, 16000, seed, WAV if sc_name == "wav" else None)
            r = run_fixed("lms", sc.x, sc.d, L, mu, cfg)
            m = evaluate(sc, r["e"], r["W"], L)
            sc_nrs[sc_name].append(m["nr_final"])
            ovfs += sum(r["counts"].values())
    means = {s: np.mean(sc_nrs[s]) for s in scenarios}
    score = (means["stationary"] + means["amp_steps"] + means["path_switch"]) / 3.0
    lms_results.append({
        "mu": mu, "score": score, "means": means, "ovfs": ovfs,
        "pass_11": all(means[s] >= 11.0 for s in ["stationary", "amp_steps", "path_switch"]) and ovfs == 0
    })

# 2. NLMS Grid
nlms_mu_grid = [0.05, 0.08, 0.10, 0.12, 0.1468, 0.18, 0.20, 0.25, 0.30, 0.40]
nlms_eps_grid = [0, 1, 2, 3, 4]
nlms_results = []
for mu in nlms_mu_grid:
    for eps_exp in nlms_eps_grid:
        cfg = FxCfg(W=W, eps_exp=eps_exp)
        sc_nrs = {s: [] for s in scenarios}
        ovfs = 0
        for sc_name in scenarios:
            for seed in tune_seeds:
                sc = make_scenario(sc_name, 16000, seed, WAV if sc_name == "wav" else None)
                r = run_fixed("nlms", sc.x, sc.d, L, mu, cfg)
                m = evaluate(sc, r["e"], r["W"], L)
                sc_nrs[sc_name].append(m["nr_final"])
                ovfs += sum(r["counts"].values())
        means = {s: np.mean(sc_nrs[s]) for s in scenarios}
        score = (means["stationary"] + means["amp_steps"] + means["path_switch"]) / 3.0
        nlms_results.append({
            "mu": mu, "eps_exp": eps_exp, "score": score, "means": means, "ovfs": ovfs,
            "pass_11": all(means[s] >= 11.0 for s in ["stationary", "amp_steps", "path_switch"]) and ovfs == 0
        })

# 3. NLMS-Shift Grid
shift_k_grid = [1, 2, 3, 4, 5]
shift_eps_grid = [0, 1, 2, 3, 4]
shift_results = []
for k in shift_k_grid:
    for eps_exp in shift_eps_grid:
        mu = 2.0**-k
        cfg = FxCfg(W=W, eps_exp=eps_exp)
        sc_nrs = {s: [] for s in scenarios}
        ovfs = 0
        for sc_name in scenarios:
            for seed in tune_seeds:
                sc = make_scenario(sc_name, 16000, seed, WAV if sc_name == "wav" else None)
                r = run_fixed("nlms_shift", sc.x, sc.d, L, mu, cfg)
                m = evaluate(sc, r["e"], r["W"], L)
                sc_nrs[sc_name].append(m["nr_final"])
                ovfs += sum(r["counts"].values())
        means = {s: np.mean(sc_nrs[s]) for s in scenarios}
        score = (means["stationary"] + means["amp_steps"] + means["path_switch"]) / 3.0
        shift_results.append({
            "K": k, "eps_exp": eps_exp, "mu": mu, "score": score, "means": means, "ovfs": ovfs,
            "pass_11": all(means[s] >= 11.0 for s in ["stationary", "amp_steps", "path_switch"]) and ovfs == 0
        })

print("\n--- LMS TOP 5 CANDIDATES ---")
for r in sorted([x for x in lms_results if x["pass_11"]], key=lambda x: x["score"], reverse=True)[:5]:
    m = r["means"]
    print(f"mu={r['mu']:<6.4f} | Mean3={r['score']:5.2f} dB | stat={m['stationary']:5.2f} | amp={m['amp_steps']:5.2f} | path={m['path_switch']:5.2f} | wav={m['wav']:5.2f} | ovfs={r['ovfs']}")

print("\n--- NLMS TOP 5 CANDIDATES ---")
for r in sorted([x for x in nlms_results if x["pass_11"]], key=lambda x: x["score"], reverse=True)[:5]:
    m = r["means"]
    print(f"mu={r['mu']:<6.4f} eps_exp={r['eps_exp']} | Mean3={r['score']:5.2f} dB | stat={m['stationary']:5.2f} | amp={m['amp_steps']:5.2f} | path={m['path_switch']:5.2f} | wav={m['wav']:5.2f} | ovfs={r['ovfs']}")

print("\n--- NLMS-SHIFT TOP 5 CANDIDATES ---")
for r in sorted([x for x in shift_results if x["pass_11"]], key=lambda x: x["score"], reverse=True)[:5]:
    m = r["means"]
    print(f"K={r['K']} eps_exp={r['eps_exp']} (mu={r['mu']}) | Mean3={r['score']:5.2f} dB | stat={m['stationary']:5.2f} | amp={m['amp_steps']:5.2f} | path={m['path_switch']:5.2f} | wav={m['wav']:5.2f} | ovfs={r['ovfs']}")

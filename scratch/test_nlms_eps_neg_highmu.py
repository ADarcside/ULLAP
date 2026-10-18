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
tune_seeds = [101, 102, 103]

print("====================================================================================")
print("NLMS EXTENDED GRID: EPS_EXP in [-2, -1], mu in [0.15 .. 0.80], SEEDS 101-103")
print("====================================================================================", flush=True)

nlms_mu_grid = [0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80]
nlms_eps_grid = [-2, -1]
results = []

for eps_exp in nlms_eps_grid:
    for mu in nlms_mu_grid:
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
        pass_11 = all(means[s] >= 11.0 for s in ["stationary", "amp_steps", "path_switch"]) and ovfs == 0
        results.append({
            "mu": mu, "eps_exp": eps_exp, "score": score, "means": means, "ovfs": ovfs, "pass_11": pass_11
        })
        print(f"eps_exp={eps_exp:2d} mu={mu:<5.2f} | score={score:5.2f} dB | stat={means['stationary']:5.2f} amp={means['amp_steps']:5.2f} path={means['path_switch']:5.2f} wav={means['wav']:5.2f} | ovf={ovfs} | pass={pass_11}", flush=True)

print("\n--- RANKED BY SCORE (Stationary + Amp_Steps + Path_Switch) / 3 ---", flush=True)
for r in sorted(results, key=lambda x: x["score"], reverse=True):
    m = r["means"]
    print(f"eps_exp={r['eps_exp']:2d} mu={r['mu']:<5.2f} | score={r['score']:5.2f} dB | stat={m['stationary']:5.2f} amp={m['amp_steps']:5.2f} path={m['path_switch']:5.2f} wav={m['wav']:5.2f} | ovfs={r['ovfs']} | pass_11={r['pass_11']}", flush=True)

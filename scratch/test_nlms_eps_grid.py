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
print("NLMS EXTENDED EPS_EXP GRID SEARCH (EPS_EXP in [-2, -1, 0, 1, 2], SEEDS 101-103)")
print("====================================================================================", flush=True)

# Test RTL compatibility first:
# In anc_core.v: localparam signed [PW-1:0] EPS_C = 64'sd1 <<< (2*F - EPS_EXP);
# With W=12, F=11, 2F=22.
# If EPS_EXP = -1, EPS_C = 2^23; if EPS_EXP = -2, EPS_C = 2^24. Both fit in PW=31 bits.
# So mathematically the RTL register width PW=31 accommodates negative EPS_EXP down to -(31-22-1) = -8.

nlms_mu_grid = [0.15, 0.20, 0.25, 0.30, 0.40]
nlms_eps_grid = [-2, -1, 0, 1, 2]
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

print("\n--- TOP 5 EXTENDED NLMS CANDIDATES ---", flush=True)
for r in sorted([x for x in results if x["pass_11"]], key=lambda x: x["score"], reverse=True)[:5]:
    m = r["means"]
    print(f"eps_exp={r['eps_exp']:2d} mu={r['mu']:<5.2f} | score={r['score']:5.2f} dB | stat={m['stationary']:5.2f} amp={m['amp_steps']:5.2f} path={m['path_switch']:5.2f} wav={m['wav']:5.2f} | ovfs={r['ovfs']}", flush=True)

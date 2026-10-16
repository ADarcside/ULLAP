"""Phase 1 task 3: fixed-point vs float for shortlisted (eps_exp, K) at W = 10, 12, 14."""
import os, sys, csv, itertools
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fixedpoint import FxCfg, run_fixed
from algos import run_float
from signals import make_scenario
from metrics import evaluate
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav"); L = 32
def job(t):
    ee, K, W, name, seed = t
    sc = make_scenario(name, 16000, seed, WAV if name == "wav" else None)
    fl = evaluate(sc, *[run_float("nlms_shift", sc.x, sc.d, L, 2.0**-K, eps=2.0**-ee)[k] for k in ("e", "W")], L)["nr_final"] if W == 12 else None
    r = run_fixed("nlms_shift", sc.x, sc.d, L, 2.0**-K, FxCfg(W=W, eps_exp=ee))
    fx = evaluate(sc, r["e"], r["W"], L)["nr_final"]
    return dict(eps_exp=ee, K=K, W=W, scenario=name, seed=seed, fixed=fx, float=fl, ovf=sum(r["counts"].values()), n=16000)
if __name__ == "__main__":
    cands = [(10, 4), (4, 3), (3, 4), (2, 3)]
    grid = [(e, k, W, s, sd) for (e, k) in cands for W in (10, 12, 14)
            for s in ("stationary", "amp_steps", "path_switch", "wav") for sd in (1, 2, 3)]
    with Pool(2) as p: rows = p.map(job, grid, chunksize=4)
    with open(os.path.join(ROOT, "results", "metrics", "eps_confirm.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, rows[0].keys()); w.writeheader(); w.writerows(rows)
    for (e, k) in cands:
        print(f"eps_exp={e} K={k}")
        for W in (10, 12, 14):
            sel = [r for r in rows if r["eps_exp"] == e and r["K"] == k and r["W"] == W]
            per = {s: np.mean([r["fixed"] for r in sel if r["scenario"] == s]) for s in ("stationary", "amp_steps", "path_switch", "wav")}
            ov = sum(r["ovf"] for r in sel)
            extra = ""
            if W == 12:
                deg = {s: np.mean([r["float"] - r["fixed"] for r in sel if r["scenario"] == s]) for s in per}
                extra = "  deg(float-fixed) " + " ".join(f"{v:+.2f}" for v in deg.values())
            print(f"  W={W:2d}  " + " ".join(f"{v:6.1f}" for v in per.values()) + f"  ovf={ov}" + extra)

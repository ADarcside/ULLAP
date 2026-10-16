"""Phase 1: regulariser (eps_exp) x step-exponent (K) sweep for NLMS-shift, fixed-point model."""
import csv, itertools, os, sys
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fixedpoint import FxCfg, run_fixed
from signals import make_scenario
from metrics import evaluate
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
L = 32
def job(t):
    W, ee, K, name, seed = t
    sc = make_scenario(name, 16000, seed, WAV if name == "wav" else None)
    r = run_fixed("nlms_shift", sc.x, sc.d, L, 2.0 ** -K, FxCfg(W=W, eps_exp=ee))
    m = evaluate(sc, r["e"], r["W"], L)
    return dict(W=W, eps_exp=ee, K=K, scenario=name, seed=seed, nr_final=m["nr_final"], nr_all=m["nr_all"],
                settle_ms=m["settle_ms"], ovf=sum(r["counts"].values()))
if __name__ == "__main__":
    W = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    grid = list(itertools.product([W], [10, 6, 5, 4, 3, 2], [3, 4, 5, 6],
                                  ["stationary", "amp_steps", "path_switch", "wav"], [1, 2, 3]))
    with Pool(2) as p: rows = p.map(job, grid, chunksize=4)
    out = os.path.join(ROOT, "results", "metrics", f"eps_sweep_W{W}.csv")
    with open(out, "w", newline="") as f:
        wr = csv.DictWriter(f, rows[0].keys()); wr.writeheader(); wr.writerows(rows)
    print(out)

import os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "py"))
from signals import make_scenario
from fixedpoint import FxCfg, run_fixed
from metrics import evaluate

WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
L = 32
cfg = FxCfg(W=12, eps_exp=2)
mu = 2.0**-3

scales = [0.25, 0.5, 1.0, 2.0, 4.0]
scenarios = ["amp_steps", "wav"]

print("=" * 95)
print("DETAILED LEVEL ROBUSTNESS & OVERFLOW / WEIGHT SATURATION AUDIT (W=12, K=3, EPS_EXP=2)")
print("=" * 95)

for sc_name in scenarios:
    print(f"\n>>> Scenario: {sc_name.upper()} <<<")
    print(f"{'Scale':5} | {'Final NR (dB)':13} | {'Whole NR (dB)':13} | {'Sat_in':6} | {'Sat_y':5} | {'Sat_e':5} | {'Sat_w':6} | {'Sat_acc':7} | {'Total Ovf':9}")
    print("-" * 95)
    for s in scales:
        fin_list, all_list = [], []
        counts_tot = {"in_x":0, "in_d":0, "y":0, "e":0, "w":0, "acc":0}
        for sd in (1, 2, 3):
            sc = make_scenario(sc_name, 16000, sd, WAV if sc_name == "wav" else None)
            r = run_fixed("nlms_shift", s * sc.x, sc.d, L, mu, cfg)
            m = evaluate(sc, r["e"], r["W"], L)
            fin_list.append(m["nr_final"])
            all_list.append(m["nr_all"])
            for k in counts_tot:
                counts_tot[k] += r["counts"].get(k, 0)
        
        c = counts_tot
        tot = sum(c.values())
        print(f"{s:5.2f} | {np.mean(fin_list):13.2f} | {np.mean(all_list):13.2f} | {c['in_x']:6d} | {c['y']:5d} | {c['e']:5d} | {c['w']:6d} | {c['acc']:7d} | {tot:9d}")

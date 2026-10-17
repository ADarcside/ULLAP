"""TASK 5: Input level robustness sweep across LMS, NLMS and NLMS-Shift."""
import os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "py"))

from signals import make_scenario
from fixedpoint import FxCfg, run_fixed
from metrics import evaluate

W = 12
L = 32
cfg = FxCfg(W=W, eps_exp=2)
WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")

def run_level_robustness():
    scenarios = ["stationary", "amp_steps", "path_switch", "wav"]
    scales = [0.25, 0.5, 1.0, 2.0, 4.0]
    algos = [
        ("LMS (mu=0.25)", "lms", 0.25, FxCfg(W=W, eps_exp=2)),
        ("NLMS (mu=0.25, eps=0)", "nlms", 0.25, FxCfg(W=W, eps_exp=0)),
        ("NLMS-Shift (K=3, eps=2)", "nlms_shift", 0.125, FxCfg(W=W, eps_exp=2))
    ]

    print("=" * 105)
    print("LEVEL ROBUSTNESS SWEEP (0.25x to 4.0x scale, W=12, L=32, Criterion: Overflow Rate < 1e-3)")
    print("=" * 105)
    header = f"{'Scale':6} | {'Algorithm':25} | {'NR avg (dB)':12} | {'Total Ovf':10} | {'Total Samples':13} | {'Ovf Rate':12} | {'Pass (< 1e-3)?'}"
    print(header)
    print("-" * len(header))

    results = []
    for scale in scales:
        for label, algo, mu, cfg_al in algos:
            nrs, total_ovf, total_samples = [], 0, 0
            for scen in scenarios:
                for seed in [1, 2, 3]:
                    sc = make_scenario(scen, 16000, seed, WAV if scen == "wav" else None)
                    x_scaled = sc.x * scale
                    r = run_fixed(algo, x_scaled, sc.d, L, mu, cfg_al)
                    m = evaluate(sc, r["e"], r["W"], L)
                    nrs.append(m["nr_avg"])
                    ovf = sum(r["counts"].values())
                    total_ovf += ovf
                    total_samples += len(sc.x)
            ovf_rate = total_ovf / total_samples
            passes = "PASS" if ovf_rate < 1e-3 else "FAIL"
            print(f"{scale:6.2f} | {label:25} | {np.mean(nrs):12.2f} | {total_ovf:10d} | {total_samples:13d} | {ovf_rate:12.2e} | {passes}")
            results.append({
                "scale": scale, "algo": label, "nr_avg": float(np.mean(nrs)),
                "ovf": total_ovf, "samples": total_samples, "rate": ovf_rate, "pass": passes
            })
    return results

if __name__ == "__main__":
    run_level_robustness()

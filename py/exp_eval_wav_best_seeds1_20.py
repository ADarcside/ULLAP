#!/usr/bin/env python3
"""Evaluate WAV-best settings across evaluation seeds 1-20."""
import os, sys
import numpy as np
import scipy.stats as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "py"))

from signals import make_scenario
from fixedpoint import FxCfg, run_fixed
from metrics import evaluate

WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
L = 32
W = 12
scenarios = ["stationary", "amp_steps", "path_switch", "wav"]
seeds = list(range(1, 21))

# The WAV-best settings selected on tuning seeds 101-103
configs = [
    ("LMS", "mu=0.125", "lms", 0.125, FxCfg(W=W, eps_exp=2)),
    ("NLMS", "eps=-2, mu=0.5", "nlms", 0.50, FxCfg(W=W, eps_exp=-2)),
    ("NLMS-Shift", "eps=0, K=2", "nlms_shift", 0.25, FxCfg(W=W, eps_exp=0)),
]

# Baseline fair-tuned means on seeds 1-20 from paper_numbers.csv
balanced = {
    "LMS": {"stationary": 22.39, "path_switch": 18.95, "amp_steps": 22.36, "wav": 5.69},
    "NLMS": {"stationary": 22.28, "path_switch": 18.53, "amp_steps": 24.16, "wav": 5.73},
    "NLMS-Shift": {"stationary": 22.37, "path_switch": 18.91, "amp_steps": 24.33, "wav": 5.46},
}

def run_eval_wav_best():
    print("=" * 110)
    print("EVALUATION OF WAV-BEST SETTINGS (SELECTED ON TUNING SEEDS 101-103) ACROSS EVAL SEEDS 1-20")
    print("=" * 110)

    results = {}
    for algo_name, setting_label, al, mu, cfg in configs:
        print(f"\n--- {algo_name} ({setting_label}) ---")
        bal = balanced[algo_name]
        results[algo_name] = {}
        for sc_name in scenarios:
            vals = []
            for s in seeds:
                sc = make_scenario(sc_name, 16000, s, WAV if sc_name == "wav" else None)
                r = run_fixed(al, sc.x, sc.d, L, mu, cfg)
                m = evaluate(sc, r["e"], r["W"], L)
                vals.append(m["nr_final"])
            
            n_samples = len(vals)
            mean_val = float(np.mean(vals))
            std_val = float(np.std(vals, ddof=1))
            t_crit = float(st.t.ppf(0.975, df=n_samples - 1))
            margin = t_crit * (std_val / np.sqrt(n_samples))
            ci_low = mean_val - margin
            ci_high = mean_val + margin
            penalty = mean_val - bal[sc_name]
            
            print(f"  {sc_name:<12} | Mean: {mean_val:5.2f} dB | 95% CI: [{ci_low:5.2f}, {ci_high:5.2f}] (margin: {margin:4.2f}) | Bal: {bal[sc_name]:5.2f} dB | Penalty: {penalty:+5.2f} dB")
            results[algo_name][sc_name] = {
                "mean": mean_val, "std": std_val, "ci_low": ci_low, "ci_high": ci_high,
                "margin": margin, "penalty": penalty
            }
    return results

if __name__ == "__main__":
    run_eval_wav_best()

#!/usr/bin/env python3
"""Evaluate WAV-best settings vs cost on synthetic scenarios across seeds 101-103."""
import os, sys, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "py"))
from signals import make_scenario
from fixedpoint import FxCfg, run_fixed
from metrics import evaluate

WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
L = 32
W = 12
scenarios = ["stationary", "amp_steps", "path_switch", "wav"]
seeds = [101, 102, 103]

def run_wav_tradeoff():
    print("=" * 90)
    print("WAV-BEST OPERATING POINTS VS COST ON SYNTHETIC SCENARIOS (SEEDS 101-103, W=12, L=32)")
    print("=" * 90, flush=True)

    # 1. LMS
    lms_candidates = [0.0625, 0.125, 0.25, 0.35, 0.5]
    lms_res = []
    for mu in lms_candidates:
        sc_nrs = {s: [] for s in scenarios}
        for sc_name in scenarios:
            for seed in seeds:
                sc = make_scenario(sc_name, 16000, seed, WAV if sc_name == "wav" else None)
                r = run_fixed("lms", sc.x, sc.d, L, mu, FxCfg(W=W))
                m = evaluate(sc, r["e"], r["W"], L)
                sc_nrs[sc_name].append(m["nr_final"])
        means = {s: np.mean(sc_nrs[s]) for s in scenarios}
        lms_res.append(("LMS", f"mu={mu}", means))
        print(f"LMS mu={mu:<6} | wav={means['wav']:5.2f} dB | stat={means['stationary']:5.2f} dB | amp={means['amp_steps']:5.2f} dB | path={means['path_switch']:5.2f} dB", flush=True)

    # 2. NLMS top candidates (from extended grid search)
    nlms_candidates = [
        (0, 0.15), (0, 0.25), (-1, 0.25), (-1, 0.50), (-2, 0.50)
    ]
    nlms_res = []
    for eps_exp, mu in nlms_candidates:
        sc_nrs = {s: [] for s in scenarios}
        for sc_name in scenarios:
            for seed in seeds:
                sc = make_scenario(sc_name, 16000, seed, WAV if sc_name == "wav" else None)
                r = run_fixed("nlms", sc.x, sc.d, L, mu, FxCfg(W=W, eps_exp=eps_exp))
                m = evaluate(sc, r["e"], r["W"], L)
                sc_nrs[sc_name].append(m["nr_final"])
        means = {s: np.mean(sc_nrs[s]) for s in scenarios}
        nlms_res.append(("NLMS", f"eps={eps_exp}, mu={mu}", means))
        print(f"NLMS eps={eps_exp} mu={mu:<4} | wav={means['wav']:5.2f} dB | stat={means['stationary']:5.2f} dB | amp={means['amp_steps']:5.2f} dB | path={means['path_switch']:5.2f} dB", flush=True)

    # 3. NLMS-Shift candidates
    shift_candidates = [
        (0, 2), (1, 2), (1, 3), (2, 3), (2, 4)
    ]
    shift_res = []
    for eps_exp, K in shift_candidates:
        sc_nrs = {s: [] for s in scenarios}
        for sc_name in scenarios:
            for seed in seeds:
                sc = make_scenario(sc_name, 16000, seed, WAV if sc_name == "wav" else None)
                r = run_fixed("nlms_shift", sc.x, sc.d, L, 2.0**-K, FxCfg(W=W, eps_exp=eps_exp))
                m = evaluate(sc, r["e"], r["W"], L)
                sc_nrs[sc_name].append(m["nr_final"])
        means = {s: np.mean(sc_nrs[s]) for s in scenarios}
        shift_res.append(("NLMS-Shift", f"eps={eps_exp}, K={K}", means))
        print(f"Shift eps={eps_exp} K={K} | wav={means['wav']:5.2f} dB | stat={means['stationary']:5.2f} dB | amp={means['amp_steps']:5.2f} dB | path={means['path_switch']:5.2f} dB", flush=True)

    best_lms = max(lms_res, key=lambda x: x[2]["wav"])
    best_nlms = max(nlms_res, key=lambda x: x[2]["wav"])
    best_shift = max(shift_res, key=lambda x: x[2]["wav"])

    print("\n--- SUMMARY TABLE: BEST WAV SETTINGS PER ALGORITHM ---", flush=True)
    print(f"{'Algorithm':12} | {'Setting':18} | {'WAV NR':10} | {'Stationary':12} | {'Amp Steps':12} | {'Path Switch':12}")
    print("-" * 85, flush=True)
    out_rows = []
    for name, setting, m in [best_lms, best_nlms, best_shift]:
        print(f"{name:12} | {setting:18} | {m['wav']:6.2f} dB  | {m['stationary']:6.2f} dB    | {m['amp_steps']:6.2f} dB   | {m['path_switch']:6.2f} dB", flush=True)
        out_rows.append({
            "algo": name, "setting": setting,
            "wav_final_nr": round(float(m["wav"]), 2),
            "stationary_final_nr": round(float(m["stationary"]), 2),
            "amp_steps_final_nr": round(float(m["amp_steps"]), 2),
            "path_switch_final_nr": round(float(m["path_switch"]), 2),
        })

    out_csv = os.path.join(ROOT, "results", "metrics", "wav_tradeoff_seeds101_103.csv")
    import csv
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["algo", "setting", "wav_final_nr", "stationary_final_nr", "amp_steps_final_nr", "path_switch_final_nr"])
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"[wav_tradeoff] Saved {len(out_rows)} rows to {out_csv}")

    return {"lms": best_lms, "nlms": best_nlms, "nlms_shift": best_shift}

if __name__ == "__main__":
    run_wav_tradeoff()

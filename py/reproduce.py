#!/usr/bin/env python3
"""Unified Reproducibility Driver for all Refinement Experiments.

Usage:
  python py/reproduce.py                  # runs all tasks (1, 2, 3, 5, 7)
  python py/reproduce.py --task 1         # runs task 1 (amp_steps reproducibility)
  python py/reproduce.py --task 2         # runs task 2 (fixed-point sweep)
  python py/reproduce.py --task 3         # runs task 3 (gate A hybrid)
  python py/reproduce.py --task 5         # runs task 5 (level robustness)
  python py/reproduce.py --task 7         # runs task 7 (acoustic feedback)
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "py"))

import csv
import numpy as np

import exp_reproduce_task1
import exp_sweep_task2
import exp_hybrid_task3
import exp_level_robustness
import exp_feedback_task7
from signals import make_scenario
from fixedpoint import FxCfg, run_fixed
from metrics import evaluate

HW_DATA = {
    "lms": {
        "setting": "W=12, mu=0.5",
        "les": 1930, "registers": 1133, "multipliers": 1,
        "fmax_slow_85c": 60.05, "slack_setup_slow_85c": 3.347, "slack_hold_slow_85c": 0.380,
        "slack_setup_slow_0c": 4.612, "slack_setup_fast_0c": 11.120,
        "latency_cycles": 35, "busy_cycles": 73
    },
    "nlms": {
        "setting": "W=12, mu=0.1468, eps_exp=2",
        "les": 2740, "registers": 1395, "multipliers": 1,
        "fmax_slow_85c": 58.87, "slack_setup_slow_85c": 3.014, "slack_hold_slow_85c": 0.395,
        "slack_setup_slow_0c": 4.220, "slack_setup_fast_0c": 10.850,
        "latency_cycles": 37, "busy_cycles": 127
    },
    "nlms_shift": {
        "setting": "W=12, K=3, EPS_EXP=2",
        "les": 2690, "registers": 1213, "multipliers": 1,
        "fmax_slow_85c": 61.98, "slack_setup_slow_85c": 3.867, "slack_hold_slow_85c": 0.402,
        "slack_setup_slow_0c": 5.177, "slack_setup_fast_0c": 11.688,
        "latency_cycles": 37, "busy_cycles": 72
    }
}


def generate_paper_numbers():
    print("[reproduce] Generating results/paper_numbers.csv...")
    wav_path = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
    scenarios = ["stationary", "amp_steps", "path_switch", "wav", "feedback"]
    algos = [("nlms_shift", 2.0**-3, FxCfg(W=12, eps_exp=2)),
             ("nlms", 0.14678, FxCfg(W=12, eps_exp=2)),
             ("lms", 0.5009, FxCfg(W=12, eps_exp=2))]
    seeds = [1, 2, 3]

    rows = []
    for al, mu, cfg in algos:
        hw = HW_DATA[al]
        for sc_name in scenarios:
            s_nrs = []
            s_all = []
            s_ovf = 0
            tot_samples = 0
            for s in seeds:
                sc = make_scenario(sc_name, 16000, s, wav_path if sc_name == "wav" else None)
                tot_samples += len(sc.x)
                r = run_fixed(al, sc.x, sc.d, 32, mu, cfg)
                m = evaluate(sc, r["e"], r["W"], 32)
                s_nrs.append(m["nr_final"])
                s_all.append(m["nr_all"])
                s_ovf += sum(r["counts"].values())

            ovf_rate = s_ovf / tot_samples
            row = {
                "algorithm": al,
                "scenario": sc_name,
                "setting": hw["setting"],
                "nr_final_mean": round(float(np.mean(s_nrs)), 2),
                "nr_final_seed1": round(float(s_nrs[0]), 2),
                "nr_final_seed2": round(float(s_nrs[1]), 2),
                "nr_final_seed3": round(float(s_nrs[2]), 2),
                "nr_all_mean": round(float(np.mean(s_all)), 2),
                "ovf_count": int(s_ovf),
                "ovf_rate": f"{ovf_rate:.6e}",
                "les": hw["les"],
                "registers": hw["registers"],
                "multipliers": hw["multipliers"],
                "fmax_slow_85c": hw["fmax_slow_85c"],
                "slack_setup_slow_85c": hw["slack_setup_slow_85c"],
                "slack_hold_slow_85c": hw["slack_hold_slow_85c"],
                "slack_setup_slow_0c": hw["slack_setup_slow_0c"],
                "slack_setup_fast_0c": hw["slack_setup_fast_0c"],
                "latency_cycles": hw["latency_cycles"],
                "busy_cycles": hw["busy_cycles"]
            }
            rows.append(row)

    # Add level robustness rows across 0.25x - 4x
    scales = [0.25, 0.50, 1.00, 2.00, 4.00]
    for scale in scales:
        for al, mu, cfg in algos:
            hw = HW_DATA[al]
            s_nrs = []
            s_all = []
            s_ovf = 0
            tot_samples = 0
            for sc_name in ["stationary", "amp_steps", "path_switch", "wav"]:
                for s in seeds:
                    sc = make_scenario(sc_name, 16000, s, wav_path if sc_name == "wav" else None)
                    x_sc = sc.x * scale
                    tot_samples += len(x_sc)
                    r = run_fixed(al, x_sc, sc.d, 32, mu, cfg)
                    m = evaluate(sc, r["e"], r["W"], 32)
                    s_nrs.append(m["nr_final"])
                    s_all.append(m["nr_all"])
                    s_ovf += sum(r["counts"].values())
            ovf_rate = s_ovf / tot_samples
            row = {
                "algorithm": al,
                "scenario": f"level_sweep_{scale:.2f}x",
                "setting": f"{hw['setting']} (input_scale={scale}x)",
                "nr_final_mean": round(float(np.mean(s_nrs)), 2),
                "nr_final_seed1": round(float(s_nrs[0]), 2),
                "nr_final_seed2": round(float(s_nrs[1]), 2),
                "nr_final_seed3": round(float(s_nrs[2]), 2),
                "nr_all_mean": round(float(np.mean(s_all)), 2),
                "ovf_count": int(s_ovf),
                "ovf_rate": f"{ovf_rate:.6e}",
                "les": hw["les"],
                "registers": hw["registers"],
                "multipliers": hw["multipliers"],
                "fmax_slow_85c": hw["fmax_slow_85c"],
                "slack_setup_slow_85c": hw["slack_setup_slow_85c"],
                "slack_hold_slow_85c": hw["slack_hold_slow_85c"],
                "slack_setup_slow_0c": hw["slack_setup_slow_0c"],
                "slack_setup_fast_0c": hw["slack_setup_fast_0c"],
                "latency_cycles": hw["latency_cycles"],
                "busy_cycles": hw["busy_cycles"]
            }
            rows.append(row)

    out_csv = os.path.join(ROOT, "results", "paper_numbers.csv")
    fieldnames = list(rows[0].keys())
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[reproduce] Successfully exported {len(rows)} verified benchmark rows to: {out_csv}")


def main():
    parser = argparse.ArgumentParser(description="Unified Refinement Reproduction Suite")
    parser.add_argument("--task", choices=["1", "2", "3", "5", "7", "all", "numbers"], default="all",
                        help="Select specific task to run (default: all)")
    args = parser.parse_args()

    t = args.task
    if t in ("1", "all"):
        exp_reproduce_task1.run_task1()
    if t in ("2", "all"):
        exp_sweep_task2.run_task2()
    if t in ("3", "all"):
        exp_hybrid_task3.run_task3()
    if t in ("5", "all"):
        exp_level_robustness.run_level_robustness()
    if t in ("7", "all"):
        exp_feedback_task7.run_feedback()

    # Generate master paper_numbers.csv
    generate_paper_numbers()


if __name__ == "__main__":
    main()


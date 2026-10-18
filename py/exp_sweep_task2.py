"""TASK 2: Fixed-point operating point sweep across EPS_EXP and K."""
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

def run_task2():
    scenarios = ["stationary", "amp_steps", "path_switch", "wav"]
    seeds = [1, 2, 3]
    eps_list = [0, 1, 2, 3, 4]
    k_list = [2, 3, 4]

    print("=" * 110)
    print("TASK 2: FIXED-POINT OPERATING POINT SWEEP (W=12, L=32, SEEDS 1-3)")
    print("=" * 110)

    header = f"{'EPS_EXP':7} | {'K':3} | {'mu':8} | {'Stationary':11} | {'Amp Steps':11} | {'Path Switch':11} | {'WAV Final':11} | {'WAV All':11} | {'Ovf (Total)':11} | {'Meets Criteria?'}"
    print(header)
    print("-" * len(header))

    out_rows = []
    for eps_exp in eps_list:
        for K in k_list:
            mu = 2.0 ** -K
            cfg = FxCfg(W=W, eps_exp=eps_exp)
            res_dict = {}
            tot_ovf = 0
            for scen in scenarios:
                fin_list, all_list = [], []
                for seed in seeds:
                    sc = make_scenario(scen, 16000, seed, WAV if scen == "wav" else None)
                    r = run_fixed("nlms_shift", sc.x, sc.d, L, mu, cfg)
                    m = evaluate(sc, r["e"], r["W"], L)
                    fin_list.append(m["nr_final"])
                    all_list.append(m["nr_all"])
                    tot_ovf += sum(r["counts"].values())
                res_dict[scen] = (np.mean(fin_list), np.mean(all_list))
            
            st_fin, st_all = res_dict["stationary"]
            as_fin, as_all = res_dict["amp_steps"]
            ps_fin, ps_all = res_dict["path_switch"]
            wv_fin, wv_all = res_dict["wav"]

            meets = (st_fin >= 11.0) and (as_fin >= 11.0) and (ps_fin >= 11.0) and (tot_ovf == 0)
            tag = "YES (PASS)" if meets else "NO"
            if eps_exp == 2 and K == 3:
                tag += " [SELECTED OP]"

            print(f"{eps_exp:7d} | {K:3d} | {mu:8.4f} | {st_fin:11.2f} | {as_fin:11.2f} | {ps_fin:11.2f} | {wv_fin:11.2f} | {wv_all:11.2f} | {tot_ovf:11d} | {tag}")
            out_rows.append({
                "eps_exp": eps_exp, "K": K, "mu": mu,
                "stationary_nr": round(float(st_fin), 2),
                "stationary_all_nr": round(float(st_all), 2),
                "amp_steps_nr": round(float(as_fin), 2),
                "amp_steps_all_nr": round(float(as_all), 2),
                "path_switch_nr": round(float(ps_fin), 2),
                "path_switch_all_nr": round(float(ps_all), 2),
                "wav_final_nr": round(float(wv_fin), 2),
                "wav_all_nr": round(float(wv_all), 2),
                "ovf_total": tot_ovf, "meets": tag
            })

    out_csv = os.path.join(ROOT, "results", "metrics", "task2_eps_k_sweep.csv")
    import csv
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["eps_exp", "K", "mu", "stationary_nr", "stationary_all_nr", "amp_steps_nr", "amp_steps_all_nr", "path_switch_nr", "path_switch_all_nr", "wav_final_nr", "wav_all_nr", "ovf_total", "meets"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"[task2] Saved {len(out_rows)} rows to {out_csv}")

if __name__ == "__main__":
    run_task2()

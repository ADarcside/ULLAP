import os, sys
import numpy as np

ROOT = r"c:\Users\Lenovo\OneDrive\Desktop\esa_proj\ULLAP"
sys.path.insert(0, os.path.join(ROOT, "py"))

from signals import make_scenario
from fixedpoint import FxCfg, run_fixed
from metrics import evaluate

WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
L = 32
W = 12
scenarios = ["stationary", "amp_steps", "path_switch", "wav"]
seeds = [1, 2, 3]

eps_list = [0, 1, 2, 3, 4]
k_list = [2, 3, 4]

print("=" * 110)
print("TASK 2: FIXED-POINT OPERATING POINT SWEEP (W=12, L=32, SEEDS 1-3)")
print("=" * 110)

header = f"{'EPS_EXP':7} | {'K':3} | {'mu':8} | {'Stationary':11} | {'Amp Steps':11} | {'Path Switch':11} | {'WAV Final':11} | {'WAV All':11} | {'Ovf (Total)':11} | {'Meets >= 10dB + 1dB Margin?'}"
print(header)
print("-" * len(header))

rows = []

for eps_exp in eps_list:
    for k in k_list:
        mu = 2.0**-k
        cfg = FxCfg(W=12, eps_exp=eps_exp)
        
        sc_res = {}
        total_ovfs = 0
        
        for s in scenarios:
            fin_nrs, all_nrs = [], []
            for seed in seeds:
                sc = make_scenario(s, 16000, seed, WAV if s == "wav" else None)
                r = run_fixed("nlms_shift", sc.x, sc.d, L, mu, cfg)
                m = evaluate(sc, r["e"], r["W"], L)
                fin_nrs.append(m["nr_final"])
                all_nrs.append(m["nr_all"])
                total_ovfs += sum(r["counts"].values())
            sc_res[s] = (np.mean(fin_nrs), np.mean(all_nrs))
            
        st_fin = sc_res["stationary"][0]
        as_fin = sc_res["amp_steps"][0]
        ps_fin = sc_res["path_switch"][0]
        wv_fin = sc_res["wav"][0]
        wv_all = sc_res["wav"][1]
        
        # Criterion: >= 10 dB on stationary, amp_steps, path_switch with >= 1 dB margin (i.e. >= 11.0 dB)
        # 0 overflows at nominal level
        meets = (st_fin >= 11.0 and as_fin >= 11.0 and ps_fin >= 11.0 and total_ovfs == 0)
        
        status_str = "YES (PASS)" if meets else "NO"
        if not meets:
            reasons = []
            if st_fin < 11.0: reasons.append(f"stat<11({st_fin:.1f})")
            if as_fin < 11.0: reasons.append(f"amp<11({as_fin:.1f})")
            if ps_fin < 11.0: reasons.append(f"path<11({ps_fin:.1f})")
            if total_ovfs > 0: reasons.append(f"ovf={total_ovfs}")
            status_str += f" ({', '.join(reasons)})"
            
        print(f"{eps_exp:7d} | {k:3d} | {mu:8.4f} | {st_fin:10.2f}  | {as_fin:10.2f}  | {ps_fin:10.2f}  | {wv_fin:10.2f}  | {wv_all:10.2f}  | {total_ovfs:11d} | {status_str}")
        
        rows.append({
            "eps_exp": eps_exp, "k": k, "mu": mu,
            "stationary_fin": st_fin, "amp_steps_fin": as_fin, "path_switch_fin": ps_fin,
            "wav_fin": wv_fin, "wav_all": wv_all, "ovf": total_ovfs, "meets": meets
        })

import os, sys
import numpy as np

ROOT = r"c:\Users\Lenovo\OneDrive\Desktop\esa_proj\ULLAP"
sys.path.insert(0, os.path.join(ROOT, "py"))

from signals import make_scenario
from fixedpoint import FxCfg, run_fixed, quantize, sat, rs
from metrics import evaluate
from numpy.lib.stride_tricks import sliding_window_view

WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
L = 32
W = 12

def run_hybrid_continuous(x, d, L, K, P_low, P_high, cfg):
    F = cfg.F or (cfg.W - 1)
    xi, _ = quantize(x, cfg.W, F)
    di, _ = quantize(d, cfg.W, F)
    n = len(x)
    X = np.concatenate([np.zeros((L - 1,), dtype=np.int64), xi])
    Xw = np.ascontiguousarray(sliding_window_view(X, L)[:, ::-1])
    
    eps_i = 1 << (2 * F - cfg.eps_exp)
    w = np.zeros(L, np.int64)
    ee = np.empty(n, np.int64)
    c = dict(acc=0, y=0, e=0, w=0)
    in_fixed_shift = False
    
    th_low = int(P_low * (1 << (2 * F)))
    th_high = int(P_high * (1 << (2 * F)))
    # Continuous shift at threshold
    fixed_s = (th_low + eps_i).bit_length() - F + K
    
    for i in range(n):
        xv = Xw[i]
        acc_raw = sum(int(wi) * int(xj) for wi, xj in zip(w, xv))
        acc, a = sat(acc_raw, cfg.acc_bits or (2 * cfg.W + 5))
        c["acc"] += a
        y, a = sat(rs(acc, F, "nearest"), cfg.W)
        c["y"] += a
        e, a = sat(int(di[i]) - y, cfg.W)
        c["e"] += a
        
        P = sum(int(xj) * int(xj) for xj in xv)
        Q = P + eps_i
        
        if in_fixed_shift:
            if P > th_high:
                in_fixed_shift = False
        else:
            if P < th_low:
                in_fixed_shift = True
                
        if in_fixed_shift:
            s = fixed_s
        else:
            s = Q.bit_length() - F + K
            
        upd = rs(e * xv.astype(object), s, "nearest").astype(np.int64)
        w, a = sat(w + upd, cfg.W)
        c["w"] += a
        ee[i] = e
        
    s_flt = float(1 << F)
    return dict(e=ee / s_flt, W=np.zeros((n, L)))

def run_check_gate_a():
    scenarios = ["stationary", "amp_steps", "path_switch", "wav"]
    seeds = [1, 2, 3]
    p_low_candidates = [0.3, 0.5, 1.0]

    # 1. EPS-only e2_k3 and e4_k3
    eps2_res = {s: [] for s in scenarios}
    eps4_res = {s: [] for s in scenarios}

    for s in scenarios:
        for seed in seeds:
            sc = make_scenario(s, 16000, seed, WAV if s == "wav" else None)
            # e2_k3
            r2 = run_fixed("nlms_shift", sc.x, sc.d, L, 2.0**-3, FxCfg(W=12, eps_exp=2))
            eps2_res[s].append(evaluate(sc, r2["e"], r2["W"], L)["nr_final"])
            # e4_k3
            r4 = run_fixed("nlms_shift", sc.x, sc.d, L, 2.0**-3, FxCfg(W=12, eps_exp=4))
            eps4_res[s].append(evaluate(sc, r4["e"], r4["W"], L)["nr_final"])

    # 2. Hybrid runs for each P_low
    hybrid_res = {pl: {s: [] for s in scenarios} for pl in p_low_candidates}

    for pl in p_low_candidates:
        ph = 1.5 * pl
        for s in scenarios:
            for seed in seeds:
                sc = make_scenario(s, 16000, seed, WAV if s == "wav" else None)
                rh = run_hybrid_continuous(sc.x, sc.d, L, 3, pl, ph, FxCfg(W=12, eps_exp=2))
                hybrid_res[pl][s].append(evaluate(sc, rh["e"], rh["W"], L)["nr_final"])

    print("==========================================================================================")
    print("GATE A RE-EVALUATION SUMMARY (Mean Final NR in dB across seeds 1-3, W=12, L=32)")
    print("==========================================================================================")
    header = f"{'Scenario':15} | {'EPS_EXP=2 K=3':14} | {'EPS_EXP=4 K=3':14} | " + " | ".join(f"{f'Hyb(Pl={pl})':14}" for pl in p_low_candidates)
    print(header)
    print("-" * len(header))

    out_rows = []
    for s in scenarios:
        e2_m = np.mean(eps2_res[s])
        e4_m = np.mean(eps4_res[s])
        p03_m = np.mean(hybrid_res[0.3][s])
        p05_m = np.mean(hybrid_res[0.5][s])
        p10_m = np.mean(hybrid_res[1.0][s])
        row = f"{s:15} | {e2_m:14.2f} | {e4_m:14.2f} | {p03_m:14.2f} | {p05_m:14.2f} | {p10_m:14.2f}"
        print(row)
        out_rows.append({
            "scenario": s,
            "eps2_k3_nr": round(float(e2_m), 2),
            "eps4_k3_nr": round(float(e4_m), 2),
            "plow_0_3_nr": round(float(p03_m), 2),
            "plow_0_5_nr": round(float(p05_m), 2),
            "plow_1_0_nr": round(float(p10_m), 2),
            "delta_plow_0_3": round(float(p03_m - e2_m), 2),
            "delta_plow_0_5": round(float(p05_m - e2_m), 2),
            "delta_plow_1_0": round(float(p10_m - e2_m), 2),
        })

    out_csv = os.path.join(ROOT, "results", "metrics", "gate_a_hybrid_sweep.csv")
    import csv
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scenario", "eps2_k3_nr", "eps4_k3_nr", "plow_0_3_nr", "plow_0_5_nr", "plow_1_0_nr", "delta_plow_0_3", "delta_plow_0_5", "delta_plow_1_0"])
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"[gate_a] Saved {len(out_rows)} rows to {out_csv}")

    print("------------------------------------------------------------------------------------------")
    print("\nDelta vs Best EPS-only (EPS_EXP=2, K=3):")
    for pl in p_low_candidates:
        print(f"\n--- Hybrid with P_low={pl}, P_high={1.5*pl:.2f} ---")
        pass_cnt = 0
        hurt_cnt = 0
        for s in scenarios:
            e2_m = np.mean(eps2_res[s])
            h_m = np.mean(hybrid_res[pl][s])
            delta = h_m - e2_m
            if delta >= 1.0: pass_cnt += 1
            if delta < 0.0: hurt_cnt += 1
            print(f"  {s:15}: {h_m:6.2f} dB (delta: {delta:+6.2f} dB)")
        print(f"  Gate A rule (>= +1.0 dB in >= 2 scenarios without hurting third): PASS_CNT={pass_cnt}, HURT_CNT={hurt_cnt}")

if __name__ == "__main__":
    run_check_gate_a()

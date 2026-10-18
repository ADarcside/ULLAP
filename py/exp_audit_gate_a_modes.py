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

def audit_hybrid_modes(x, d, L, K, P_low, P_high, cfg):
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
    fixed_s = (th_low + eps_i).bit_length() - F + K
    
    fixed_count = 0
    norm_count = 0
    switches = 0
    p_vals = []
    
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
        p_vals.append(P / (1 << (2 * F)))
        Q = P + eps_i
        
        prev_mode = in_fixed_shift
        if in_fixed_shift:
            if P > th_high:
                in_fixed_shift = False
                switches += 1
        else:
            if P < th_low:
                in_fixed_shift = True
                switches += 1
                
        if in_fixed_shift:
            s = fixed_s
            fixed_count += 1
        else:
            s = Q.bit_length() - F + K
            norm_count += 1
            
        upd = rs(e * xv.astype(object), s, "nearest").astype(np.int64)
        w, a = sat(w + upd, cfg.W)
        c["w"] += a
        ee[i] = e
        
    s_flt = float(1 << F)
    return dict(
        e=ee / s_flt, 
        W=np.zeros((n, L)), 
        fixed_count=fixed_count, 
        norm_count=norm_count, 
        switches=switches, 
        fixed_s=fixed_s,
        min_p=min(p_vals),
        max_p=max(p_vals),
        mean_p=float(np.mean(p_vals))
    )

def run_audit_gate_a():
    scenarios = ["stationary", "amp_steps", "path_switch", "wav"]
    seeds = [1, 2, 3]
    p_lows = [0.3, 0.5, 1.0]

    print("==========================================================================================")
    print("GATE A MODE FRACTION AUDIT (L=32, W=12, EPS_EXP=2, K=3)")
    print("==========================================================================================")

    for pl in p_lows:
        ph = 1.5 * pl
        print(f"\n--- P_low = {pl:.1f}, P_high = {ph:.2f} ---")
        th_l = int(pl * (1 << 22))
        eps_i = 1 << 20
        fixed_s = (th_l + eps_i).bit_length() - 11 + 3
        print(f"  th_low (raw) = {th_l}, eps_i = {eps_i}, sum = {th_l + eps_i}, bit_len = {(th_l + eps_i).bit_length()}, fixed_s = {fixed_s}")
        
        for sc_name in scenarios:
            fixed_fracs = []
            switch_counts = []
            min_ps = []
            max_ps = []
            mean_ps = []
            nrs = []
            for seed in seeds:
                sc = make_scenario(sc_name, 16000, seed, WAV if sc_name == "wav" else None)
                res = audit_hybrid_modes(sc.x, sc.d, L, 3, pl, ph, FxCfg(W=12, eps_exp=2))
                ff = res["fixed_count"] / (res["fixed_count"] + res["norm_count"])
                fixed_fracs.append(ff)
                switch_counts.append(res["switches"])
                min_ps.append(res["min_p"])
                max_ps.append(res["max_p"])
                mean_ps.append(res["mean_p"])
                nr = evaluate(sc, res["e"], res["W"], L)["nr_final"]
                nrs.append(nr)
                
            print(f"  {sc_name:15}: Mean NR = {np.mean(nrs):6.2f} dB | Fixed Mode Frac = {np.mean(fixed_fracs)*100:6.2f}% (Norm: {(1-np.mean(fixed_fracs))*100:6.2f}%) | Switches = {np.mean(switch_counts):4.1f} | P range: [{np.mean(min_ps):.4f}, {np.mean(max_ps):.4f}], mean P = {np.mean(mean_ps):.4f}")

if __name__ == "__main__":
    run_audit_gate_a()

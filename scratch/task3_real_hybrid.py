import os, sys
import numpy as np

ROOT = r"c:\Users\Lenovo\OneDrive\Desktop\esa_proj\ULLAP"
sys.path.insert(0, os.path.join(ROOT, "py"))

from signals import make_scenario
from fixedpoint import FxCfg, run_fixed, quantize, sat, rs
from metrics import evaluate

WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
L = 32
W = 12
scenarios = ["stationary", "amp_steps", "path_switch", "wav"]
seeds = [1, 2, 3]

print("=" * 100)
print("TASK 3: GATE A RERUN WITH REAL HYBRID AND POWER PERCENTILE PROFILING")
print("=" * 100)

# Step 1: Compute distribution of P = sum(x^2) across 32 taps in floating-point [0, 1) and integer Q units
all_P = {s: [] for s in scenarios}
F = W - 1 # 11 bits

for s in scenarios:
    for seed in seeds:
        sc = make_scenario(s, 16000, seed, WAV if s == "wav" else None)
        xi, _ = quantize(sc.x, W, F)
        # Compute sliding 32-tap sum of x^2 in normalized float units
        X = np.concatenate([np.zeros(L - 1), sc.x])
        from numpy.lib.stride_tricks import sliding_window_view
        Xw = sliding_window_view(X, L)
        P_vals = (Xw**2).sum(axis=1)
        all_P[s].extend(P_vals)

print("\n--- Sliding Window Power P = sum(x^2) Percentiles (L=32 taps) ---")
print(f"{'Scenario':15} | {'10th %':10} | {'25th %':10} | {'50th % (Med)':12} | {'75th %':10} | {'90th %':10}")
print("-" * 75)

p_pct = {}
for s in scenarios:
    arr = np.array(all_P[s])
    p10, p25, p50, p75, p90 = np.percentile(arr, [10, 25, 50, 75, 90])
    p_pct[s] = (p10, p25, p50, p75, p90)
    print(f"{s:15} | {p10:10.5f} | {p25:10.5f} | {p50:12.5f} | {p75:10.5f} | {p90:10.5f}")

# Overall median across stationary/all scenarios
overall_p25 = np.percentile(all_P["stationary"], 25)
overall_p50 = np.percentile(all_P["stationary"], 50)
print(f"\nSelected Hybrid Candidates based on distribution:")
print(f"Candidate 1 (25th percentile of stationary): P_low = {overall_p25:.5f}, P_high = {1.5*overall_p25:.5f}")
print(f"Candidate 2 (50th percentile of stationary): P_low = {overall_p50:.5f}, P_high = {1.5*overall_p50:.5f}")

# Also test a lower threshold to capture quiet regions in wav / amp_steps
p_quiet_25 = np.percentile(all_P["wav"], 25)
print(f"Candidate 3 (25th percentile of WAV):        P_low = {p_quiet_25:.5f}, P_high = {1.5*p_quiet_25:.5f}")

def run_real_hybrid(x, d, L, K, P_low, P_high, cfg):
    F = cfg.F or (cfg.W - 1)
    xi, _ = quantize(x, cfg.W, F)
    di, _ = quantize(d, cfg.W, F)
    n = len(x)
    X = np.concatenate([np.zeros((L - 1,), dtype=np.int64), xi])
    from numpy.lib.stride_tricks import sliding_window_view
    Xw = np.ascontiguousarray(sliding_window_view(X, L)[:, ::-1])
    
    eps_i = 1 << (2 * F - cfg.eps_exp)
    w = np.zeros(L, np.int64)
    ee = np.empty(n, np.int64)
    
    # Scale thresholds to integer Q units
    th_low = int(P_low * (1 << (2 * F)))
    th_high = int(P_high * (1 << (2 * F)))
    
    in_fixed_shift = False
    fixed_count = 0
    
    for i in range(n):
        xv = Xw[i]
        acc_raw = sum(int(wi) * int(xj) for wi, xj in zip(w, xv))
        acc, _ = sat(acc_raw, cfg.acc_bits or (2 * cfg.W + 5))
        y, _ = sat(rs(acc, F, "nearest"), cfg.W)
        e, _ = sat(int(di[i]) - y, cfg.W)
        
        P = sum(int(xj) * int(xj) for xj in xv)
        Q = P + eps_i
        
        # Hysteresis
        if in_fixed_shift:
            if P > th_high:
                in_fixed_shift = False
        else:
            if P < th_low:
                in_fixed_shift = True
                
        if in_fixed_shift:
            fixed_count += 1
            # Continuous shift formulation
            s = (th_low + eps_i).bit_length() - F + K
        else:
            s = Q.bit_length() - F + K
            
        upd = rs(e * xv.astype(object), s, "nearest").astype(np.int64)
        w, _ = sat(w + upd, cfg.W)
        ee[i] = e
        
    s_flt = float(1 << F)
    return dict(e=ee / s_flt, W=np.zeros((n, L)), fixed_fraction=fixed_count / n)

# Run comparison
print("\n" + "=" * 100)
print("EVALUATING HYBRID CANDIDATES VS EPS-ONLY (EPS_EXP=2, K=3)")
print("=" * 100)

candidates = [
    ("Candidate 1 (P25_stat)", overall_p25, 1.5 * overall_p25),
    ("Candidate 2 (P50_stat)", overall_p50, 1.5 * overall_p50),
    ("Candidate 3 (P25_wav)",  p_quiet_25, 1.5 * p_quiet_25)
]

# Baseline EPS-only results
eps_baseline = {}
for s in scenarios:
    vals = []
    for seed in seeds:
        sc = make_scenario(s, 16000, seed, WAV if s == "wav" else None)
        r = run_fixed("nlms_shift", sc.x, sc.d, L, 2.0**-3, FxCfg(W=12, eps_exp=2))
        vals.append(evaluate(sc, r["e"], r["W"], L)["nr_final"])
    eps_baseline[s] = np.mean(vals)

for name, pl, ph in candidates:
    print(f"\n>>> {name}: P_low = {pl:.5f}, P_high = {ph:.5f} <<<")
    print(f"{'Scenario':15} | {'EPS-Only (dB)':14} | {'Hybrid (dB)':14} | {'Delta (dB)':12} | {'Fixed Mode %':14}")
    print("-" * 75)
    
    deltas = {}
    for s in scenarios:
        h_vals, frac_vals = [], []
        for seed in seeds:
            sc = make_scenario(s, 16000, seed, WAV if s == "wav" else None)
            rh = run_real_hybrid(sc.x, sc.d, L, 3, pl, ph, FxCfg(W=12, eps_exp=2))
            h_vals.append(evaluate(sc, rh["e"], rh["W"], L)["nr_final"])
            frac_vals.append(rh["fixed_fraction"])
        h_mean = np.mean(h_vals)
        frac_mean = np.mean(frac_vals) * 100.0
        delta = h_mean - eps_baseline[s]
        deltas[s] = delta
        print(f"{s:15} | {eps_baseline[s]:14.2f} | {h_mean:14.2f} | {delta:+12.2f} | {frac_mean:13.1f}%")
        
    # Check Gate A rule:
    # Adopt ONLY if hybrid beats eps-only by >= 1.0 dB in at least two scenarios without hurting the third by more than 0.5 dB
    beat_cnt = sum(1 for s in scenarios if deltas[s] >= 1.0)
    hurt_cnt = sum(1 for s in scenarios if deltas[s] < -0.5)
    
    print(f"Gate A Evaluation: Scenarios with Delta >= +1.0 dB: {beat_cnt} | Scenarios degraded by > 0.5 dB: {hurt_cnt}")
    if beat_cnt >= 2 and hurt_cnt == 0:
        print(">>> VERDICT: ADOPT HYBRID <<<")
    else:
        print(">>> VERDICT: REJECT HYBRID (Fails Gate A Rule) <<<")

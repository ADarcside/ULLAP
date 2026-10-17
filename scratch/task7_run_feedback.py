import os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "py"))

from signals import make_scenario
from algos import run_float
from fixedpoint import FxCfg, run_fixed
from metrics import evaluate

L = 32
W = 12
cfg = FxCfg(W=12, eps_exp=2)
mu_dict = {
    "lms": 0.5,
    "nlms": 0.5,
    "nlms_shift": 2.0**-3
}

print("=" * 100)
print("TASK 7: ACOUSTIC FEEDBACK (HOWLING) SCENARIO EVALUATION")
print("=" * 100)

seeds = [1, 2, 3]

# 1. Floating-point and Fixed-point evaluation on the feedback scenario
algos = ["lms", "nlms", "nlms_shift"]

print("\n--- 1. Open-Loop Reference-Noise ANC on Acoustic Feedback Scenario ---")
print(f"{'Algorithm':12} | {'Mode':6} | {'Final NR (dB)':14} | {'Whole NR (dB)':14} | {'Total Overflows':15} | {'Diverged?':10}")
print("-" * 85)

for al in algos:
    # Float
    flt_fin, flt_all = [], []
    for sd in seeds:
        sc = make_scenario("feedback", 16000, sd)
        rf = run_float(al, sc.x, sc.d, L, mu_dict[al])
        m = evaluate(sc, rf["e"], rf["W"], L)
        flt_fin.append(m["nr_final"])
        flt_all.append(m["nr_all"])
        
    div_flt = np.isnan(flt_fin).any() or np.isinf(flt_fin).any() or (np.mean(flt_fin) < -50.0)
    print(f"{al:12} | {'Float':6} | {np.mean(flt_fin):14.2f} | {np.mean(flt_all):14.2f} | {'N/A (float)':15} | {'YES' if div_flt else 'NO (Stable)':10}")

    # Fixed W=12
    fx_fin, fx_all = [], []
    ovf_tot = 0
    for sd in seeds:
        sc = make_scenario("feedback", 16000, sd)
        rx = run_fixed(al, sc.x, sc.d, L, mu_dict[al], cfg)
        m = evaluate(sc, rx["e"], rx["W"], L)
        fx_fin.append(m["nr_final"])
        fx_all.append(m["nr_all"])
        ovf_tot += sum(rx["counts"].values())
        
    div_fx = np.isnan(fx_fin).any() or np.isinf(fx_fin).any() or (np.mean(fx_fin) < -50.0)
    print(f"{al:12} | {'W=12':6} | {np.mean(fx_fin):14.2f} | {np.mean(fx_all):14.2f} | {ovf_tot:15d} | {'YES' if div_fx else 'NO (Stable)':10}")

# 2. Closed-Loop Active Feedback Cancellation Test (AFC)
# If the speaker output e[n] is fed back into microphone d[n] sample-by-sample:
print("\n--- 2. Closed-Loop Sample-by-Sample Dynamic Feedback Simulation ---")
print("Testing whether feeding speaker output e[n] back into mic d[n] causes divergence:")

def simulate_closed_loop(algo, g_loop=0.88, D_loop=8):
    r = np.random.default_rng(1)
    n = 8000
    from signals import speech_like, BASE_RMS, make_paths
    s = speech_like(n)
    h1, _ = make_paths()
    v = BASE_RMS * r.standard_normal(n)
    nz = np.convolve(v, h1)[:n]
    
    # Run closed loop sample by sample in floating point
    w = np.zeros(L)
    X = np.zeros(L)
    e_buf = np.zeros(n + D_loop + 1)
    e_out = np.zeros(n)
    
    for i in range(n):
        # Microphone input = clean speech + noise + delayed speaker feedback
        d_i = s[i] + nz[i] + g_loop * e_buf[i] # e[i - D_loop]
        
        # Reference noise mic
        X = np.roll(X, 1)
        X[0] = v[i]
        
        y_i = np.dot(w, X)
        e_i = d_i - y_i
        
        # update
        if algo == "lms":
            w += 0.5 * e_i * X
        elif algo == "nlms":
            P = np.dot(X, X) + 0.25
            w += (0.5 / P) * e_i * X
        elif algo == "nlms_shift":
            P = np.dot(X, X) + 0.25
            s_shift = int(np.floor(np.log2(P)))
            w += (2.0**-(s_shift + 3)) * e_i * X
            
        e_buf[i + D_loop] = e_i
        e_out[i] = e_i
        
    p_mic = np.mean((s + nz)**2)
    p_res = np.mean(e_out[4000:]**2)
    suppression = 10 * np.log10(p_mic / max(1e-12, p_res))
    max_val = np.max(np.abs(e_out))
    diverged = max_val > 10.0 or np.isnan(max_val)
    return suppression, max_val, diverged

for al in algos:
    sup, mx, div = simulate_closed_loop(al)
    print(f"Closed-loop {al:12}: Suppression = {sup:6.2f} dB, Max Amplitude = {mx:6.2f}, Diverged = {'YES' if div else 'NO (Stable)'}")

print("\n" + "=" * 100)
print("TASK 7 ANALYSIS & SCIENTIFIC LIMITATIONS:")
print("=" * 100)

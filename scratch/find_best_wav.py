import os, sys, numpy as np

ROOT = r"c:\Users\Lenovo\OneDrive\Desktop\esa_proj\ULLAP"
sys.path.insert(0, os.path.join(ROOT, "py"))
from signals import make_scenario
from fixedpoint import FxCfg, run_fixed
from metrics import evaluate

WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
L = 32
W = 12
scenarios = ["stationary", "amp_steps", "path_switch", "wav"]
seeds = [101, 102, 103]

# 1. LMS sweep over mu in [0.03125 .. 0.5]
lms_res = []
for mu in [0.03125, 0.0625, 0.125, 0.25, 0.5]:
    cfg = FxCfg(W=W, eps_exp=2)
    sc_nrs = {s: [] for s in scenarios}
    for sc_name in scenarios:
        for seed in seeds:
            sc = make_scenario(sc_name, 16000, seed, WAV if sc_name == "wav" else None)
            r = run_fixed("lms", sc.x, sc.d, L, mu, cfg)
            m = evaluate(sc, r["e"], r["W"], L)
            sc_nrs[sc_name].append(m["nr_final"])
    means = {s: np.mean(sc_nrs[s]) for s in scenarios}
    lms_res.append(("LMS", f"mu={mu}", means))

# 2. NLMS sweep
nlms_res = []
for eps_exp in [-2, -1, 0, 1, 2]:
    for mu in [0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        cfg = FxCfg(W=W, eps_exp=eps_exp)
        sc_nrs = {s: [] for s in scenarios}
        for sc_name in scenarios:
            for seed in seeds:
                sc = make_scenario(sc_name, 16000, seed, WAV if sc_name == "wav" else None)
                r = run_fixed("nlms", sc.x, sc.d, L, mu, cfg)
                m = evaluate(sc, r["e"], r["W"], L)
                sc_nrs[sc_name].append(m["nr_final"])
        means = {s: np.mean(sc_nrs[s]) for s in scenarios}
        nlms_res.append(("NLMS", f"eps={eps_exp}, mu={mu}", means))

# 3. NLMS-Shift sweep
shift_res = []
for eps_exp in [0, 1, 2, 3, 4]:
    for K in [2, 3, 4]:
        cfg = FxCfg(W=W, eps_exp=eps_exp)
        sc_nrs = {s: [] for s in scenarios}
        for sc_name in scenarios:
            for seed in seeds:
                sc = make_scenario(sc_name, 16000, seed, WAV if sc_name == "wav" else None)
                r = run_fixed("nlms_shift", sc.x, sc.d, L, 2.0**-K, cfg)
                m = evaluate(sc, r["e"], r["W"], L)
                sc_nrs[sc_name].append(m["nr_final"])
        means = {s: np.mean(sc_nrs[s]) for s in scenarios}
        shift_res.append(("NLMS-Shift", f"eps={eps_exp}, K={K}", means))

best_lms_wav = max(lms_res, key=lambda x: x[2]["wav"])
best_nlms_wav = max(nlms_res, key=lambda x: x[2]["wav"])
best_shift_wav = max(shift_res, key=lambda x: x[2]["wav"])

print("==========================================================================================")
print("WAV-BEST OPERATING POINTS VS COST ON SYNTHETIC SCENARIOS (SEEDS 101-103)")
print("==========================================================================================")
print(f"{'Algorithm':12} | {'WAV-Best Setting':18} | {'WAV NR':10} | {'Stationary':12} | {'Amp Steps':12} | {'Path Switch':12}")
print("-" * 85)
for name, setting, m in [best_lms_wav, best_nlms_wav, best_shift_wav]:
    print(f"{name:12} | {setting:18} | {m['wav']:6.2f} dB  | {m['stationary']:6.2f} dB    | {m['amp_steps']:6.2f} dB   | {m['path_switch']:6.2f} dB")

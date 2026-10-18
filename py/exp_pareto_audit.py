import os, sys, time, shutil
import multiprocessing as mp
import numpy as np
import scipy.stats as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "py"))

from signals import make_scenario
from fixedpoint import FxCfg, run_fixed
from metrics import evaluate

W = 12
L = 32
N = 16000
SEEDS = list(range(1, 21))

# Worker function for parallel execution
def eval_task(task):
    algo, mu, cfg, k, scen, seed = task
    sc = make_scenario(scen, N, seed, None)
    r = run_fixed(algo, sc.x, sc.d, L, mu, cfg)
    m = evaluate(sc, r["e"], r["W"], L)
    return (algo, mu, cfg.eps_exp, k, scen, seed, m["nr_final"])

def main():
    print("=" * 100)
    print("PARETO FRONTIER AUDIT: STATIONARY VS AMP_STEPS ACROSS SEEDS 1-20 (W=12, L=32)")
    print("=" * 100)
    
    # Define configurations
    lms_mu_grid = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 1.0]
    nlms_mu_grid = [0.05, 0.08, 0.10, 0.12, 0.1468, 0.18, 0.20, 0.25, 0.30, 0.40]
    nlms_eps_grid = [0, 1, 2, 3, 4]
    shift_k_grid = [1, 2, 3, 4, 5]
    shift_eps_grid = [0, 1, 2, 3, 4]
    
    tasks = []
    
    # 1. LMS tasks
    for mu in lms_mu_grid:
        cfg = FxCfg(W=W, eps_exp=2)
        for scen in ["stationary", "amp_steps"]:
            for seed in SEEDS:
                tasks.append(("lms", mu, cfg, None, scen, seed))
                
    # 2. NLMS tasks
    for mu in nlms_mu_grid:
        for eps in nlms_eps_grid:
            cfg = FxCfg(W=W, eps_exp=eps)
            for scen in ["stationary", "amp_steps"]:
                for seed in SEEDS:
                    tasks.append(("nlms", mu, cfg, None, scen, seed))
                    
    # 3. NLMS-Shift tasks
    for k in shift_k_grid:
        mu = 2.0**-k
        for eps in shift_eps_grid:
            cfg = FxCfg(W=W, eps_exp=eps)
            for scen in ["stationary", "amp_steps"]:
                for seed in SEEDS:
                    tasks.append(("nlms_shift", mu, cfg, k, scen, seed))
                    
    total_tasks = len(tasks)
    print(f"Total tasks to execute: {total_tasks} across {mp.cpu_count()} CPU cores...")
    t0 = time.time()
    
    with mp.Pool(processes=min(12, mp.cpu_count())) as pool:
        results = pool.map(eval_task, tasks)
        
    print(f"All simulations finished in {time.time() - t0:.1f}s.")
    
    # Organize results by setting
    # key: (algo, label) -> dict of scen -> list of 20 vals
    data = {}
    for r in results:
        algo, mu, eps, k, scen, seed, nr = r
        if algo == "lms":
            label = f"mu={mu}"
            key = ("lms", label)
        elif algo == "nlms":
            label = f"mu={mu}, eps={eps}"
            key = ("nlms", label)
        else:
            label = f"K={k}, eps={eps}"
            key = ("nlms_shift", label)
            
        if key not in data:
            data[key] = {"stationary": [], "amp_steps": []}
        data[key][scen].append(nr)
        
    # Aggregate stats per setting
    stats = []
    for (algo, label), sc_dict in data.items():
        stat_vals = sc_dict["stationary"]
        amp_vals = sc_dict["amp_steps"]
        
        n = len(stat_vals)
        t_crit = float(st.t.ppf(0.975, df=n - 1))
        
        stat_m = float(np.mean(stat_vals))
        stat_s = float(np.std(stat_vals, ddof=1))
        stat_margin = t_crit * (stat_s / np.sqrt(n))
        
        amp_m = float(np.mean(amp_vals))
        amp_s = float(np.std(amp_vals, ddof=1))
        amp_margin = t_crit * (amp_s / np.sqrt(n))
        
        stats.append({
            "algo": algo,
            "label": label,
            "stat_mean": stat_m,
            "stat_ci_low": stat_m - stat_margin,
            "stat_ci_high": stat_m + stat_margin,
            "stat_margin": stat_margin,
            "amp_mean": amp_m,
            "amp_ci_low": amp_m - amp_margin,
            "amp_ci_high": amp_m + amp_margin,
            "amp_margin": amp_margin,
        })
        
    print("\n" + "=" * 115)
    print("LMS SETTINGS EVALUATION ON SEEDS 1-20 (CHECK FOR STAT >= 22.0 AND AMP >= 24.0)")
    print("=" * 115)
    lms_stats = [s for s in stats if s["algo"] == "lms"]
    lms_passed_mean = []
    lms_passed_ci = []
    for s in sorted(lms_stats, key=lambda x: x["stat_mean"], reverse=True):
        hit_mean = (s["stat_mean"] >= 22.0 and s["amp_mean"] >= 24.0)
        hit_ci = (s["stat_ci_low"] >= 22.0 and s["amp_ci_low"] >= 24.0)
        if hit_mean: lms_passed_mean.append(s)
        if hit_ci: lms_passed_ci.append(s)
        print(f"LMS {s['label']:<10} | Stationary: {s['stat_mean']:5.2f} dB [{s['stat_ci_low']:5.2f}, {s['stat_ci_high']:5.2f}] | Amp Steps: {s['amp_mean']:5.2f} dB [{s['amp_ci_low']:5.2f}, {s['amp_ci_high']:5.2f}] | Hit(Mean): {str(hit_mean):<5} | Hit(95% CI): {str(hit_ci):<5}")
        
    print("\n--- LMS AUDIT VERDICT ---")
    if lms_passed_ci:
        print(f"LMS Settings meeting BOTH >=22 dB stationary and >=24 dB amp_steps (95% CI): {[x['label'] for x in lms_passed_ci]}")
    elif lms_passed_mean:
        print(f"LMS Settings meeting BOTH >=22 dB stationary and >=24 dB amp_steps (Mean only): {[x['label'] for x in lms_passed_mean]}")
    else:
        print("ZERO LMS settings in the entire grid can reach >= 22.0 dB stationary and >= 24.0 dB amp_steps simultaneously (neither by mean nor by 95% CI).")

    print("\n" + "=" * 115)
    print("NLMS-SHIFT SETTINGS MEETING BOTH STAT >= 22.0 AND AMP >= 24.0")
    print("=" * 115)
    shift_stats = [s for s in stats if s["algo"] == "nlms_shift"]
    for s in sorted(shift_stats, key=lambda x: x["stat_mean"], reverse=True):
        hit_mean = (s["stat_mean"] >= 22.0 and s["amp_mean"] >= 24.0)
        hit_ci = (s["stat_ci_low"] >= 22.0 and s["amp_ci_low"] >= 24.0)
        if hit_mean or hit_ci:
            print(f"NLMS-Shift {s['label']:<15} | Stationary: {s['stat_mean']:5.2f} dB [{s['stat_ci_low']:5.2f}, {s['stat_ci_high']:5.2f}] | Amp Steps: {s['amp_mean']:5.2f} dB [{s['amp_ci_low']:5.2f}, {s['amp_ci_high']:5.2f}] | Hit(Mean): {str(hit_mean):<5} | Hit(95% CI): {str(hit_ci):<5}")

    print("\n" + "=" * 115)
    print("NLMS SETTINGS MEETING BOTH STAT >= 22.0 AND AMP >= 24.0")
    print("=" * 115)
    nlms_stats = [s for s in stats if s["algo"] == "nlms"]
    for s in sorted(nlms_stats, key=lambda x: x["stat_mean"], reverse=True):
        hit_mean = (s["stat_mean"] >= 22.0 and s["amp_mean"] >= 24.0)
        hit_ci = (s["stat_ci_low"] >= 22.0 and s["amp_ci_low"] >= 24.0)
        if hit_mean or hit_ci:
            print(f"NLMS {s['label']:<18} | Stationary: {s['stat_mean']:5.2f} dB [{s['stat_ci_low']:5.2f}, {s['stat_ci_high']:5.2f}] | Amp Steps: {s['amp_mean']:5.2f} dB [{s['amp_ci_low']:5.2f}, {s['amp_ci_high']:5.2f}] | Hit(Mean): {str(hit_mean):<5} | Hit(95% CI): {str(hit_ci):<5}")

    # Generate Pareto Plot
    fig, ax = plt.subplots(figsize=(9, 6.5))
    
    # Target Box: stat >= 22.0, amp >= 24.0
    ax.axvspan(22.0, 30.0, ymin=0.0, ymax=1.0, color='gray', alpha=0.08)
    ax.axhspan(24.0, 30.0, xmin=0.0, xmax=1.0, color='gray', alpha=0.08)
    ax.fill_between([22.0, 30.0], 24.0, 30.0, color='lightgreen', alpha=0.25, label="High-Performance Target Zone (Stat>=22 dB, Amp>=24 dB)")
    ax.axvline(22.0, color='black', linestyle=':', lw=1.2)
    ax.axhline(24.0, color='black', linestyle=':', lw=1.2)
    
    # Plot LMS points
    lms_x = [s["stat_mean"] for s in lms_stats]
    lms_y = [s["amp_mean"] for s in lms_stats]
    ax.scatter(lms_x, lms_y, color='#1f77b4', s=45, alpha=0.7, label='LMS (Fixed Step, all mu)', marker='o')
    for s in lms_stats:
        if s["label"] in ["mu=0.1", "mu=0.25", "mu=0.5", "mu=0.8"]:
            ax.annotate(s["label"], (s["stat_mean"] + 0.15, s["amp_mean"] - 0.2), fontsize=8, color='#1f77b4')
            
    # Plot NLMS points
    nlms_x = [s["stat_mean"] for s in nlms_stats]
    nlms_y = [s["amp_mean"] for s in nlms_stats]
    ax.scatter(nlms_x, nlms_y, color='#ff7f0e', s=45, alpha=0.7, label='NLMS (Normalized, all mu x eps)', marker='s')
    
    # Plot NLMS-Shift points
    shift_x = [s["stat_mean"] for s in shift_stats]
    shift_y = [s["amp_mean"] for s in shift_stats]
    ax.scatter(shift_x, shift_y, color='#2ca02c', s=60, alpha=0.85, label='NLMS-Shift (all K x eps)', marker='^')
    for s in shift_stats:
        if s["label"] in ["K=3, eps=2", "K=2, eps=1", "K=4, eps=3"]:
            ax.annotate(s["label"], (s["stat_mean"] + 0.15, s["amp_mean"] + 0.15), fontsize=8, fontweight='bold', color='#2ca02c')

    ax.set_title("Pareto Trade-off: Stationary vs Amplitude Steps Noise Reduction (Seeds 1-20, W=12)")
    ax.set_xlabel("Stationary Final Noise Reduction (dB)")
    ax.set_ylabel("Amplitude Steps Final Noise Reduction (dB)")
    ax.set_xlim(5, 25)
    ax.set_ylim(10, 26)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='lower left', framealpha=0.9)
    
    out_png = os.path.join(ROOT, "results", "plots", "fig12_pareto_stationary_amp_steps.png")
    out_pdf = os.path.join(ROOT, "results", "plots", "fig12_pareto_stationary_amp_steps.pdf")
    fig.savefig(out_png, dpi=300, bbox_inches='tight')
    fig.savefig(out_pdf, bbox_inches='tight')
    plt.close(fig)
    print(f"\nPareto plot saved to:\n  - {out_png}\n  - {out_pdf}")

    # Mirror to docs/figures
    shutil.copy2(out_png, os.path.join(ROOT, "docs", "figures", "fig12_pareto_stationary_amp_steps.png"))

    # Save summary CSV
    import csv
    csv_path = os.path.join(ROOT, "results", "metrics", "pareto_evaluation_seeds1_20.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["algo", "label", "stat_mean", "stat_ci_low", "stat_ci_high", "amp_mean", "amp_ci_low", "amp_ci_high"])
        writer.writeheader()
        for s in stats:
            writer.writerow({
                "algo": s["algo"], "label": s["label"],
                "stat_mean": s["stat_mean"], "stat_ci_low": s["stat_ci_low"], "stat_ci_high": s["stat_ci_high"],
                "amp_mean": s["amp_mean"], "amp_ci_low": s["amp_ci_low"], "amp_ci_high": s["amp_ci_high"]
            })
    print(f"Pareto CSV saved to: {csv_path}")
    return stats

def run_pareto_audit():
    return main()

if __name__ == "__main__":
    main()

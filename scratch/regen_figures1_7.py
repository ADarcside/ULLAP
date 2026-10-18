import os, sys
import numpy as np

ROOT = r"c:\Users\Lenovo\OneDrive\Desktop\esa_proj\ULLAP"
sys.path.insert(0, os.path.join(ROOT, "py"))

from signals import make_scenario, SCENARIOS
from fixedpoint import FxCfg, run_fixed
from metrics import curves, evaluate, FS
from visualize import (
    plot_fig1_convergence, plot_fig2_waveforms, plot_fig3_residual_error,
    plot_fig4_tracking_response, plot_fig5_noise_reduction_comparison,
    plot_fig6_bitwidth_sweep, plot_fig7_coef_trajectories
)

WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
L = 32
W = 12
N = 16000

# Fair-tuned parameters at W=12
ALGOS = [
    ("lms", 0.25, FxCfg(W=W, eps_exp=2)),
    ("nlms", 0.25, FxCfg(W=W, eps_exp=0)),
    ("nlms_shift", 0.125, FxCfg(W=W, eps_exp=2)),  # K=3
]

scenarios = ["stationary", "amp_steps", "path_switch", "wav", "feedback"]
seed = 1

print("=" * 90)
print("REGENERATING FIGURES 1-7 USING FAIR-TUNED SETTINGS (W=12, L=32, Seed 1)")
print("  LMS: mu=0.25 | NLMS: mu=0.25, eps_exp=0 | NLMS-Shift: K=3, eps_exp=2")
print("=" * 90)

sc_curves, sc_events, sc_res_pows = {}, {}, {}
primary_d, ref_x, clean_s, err_sigs, W_traj = {}, {}, {}, {}, {}
summary_plot_data = {sc: {} for sc in scenarios}

time_vec = np.arange(N) / FS

for sc_name in scenarios:
    sc = make_scenario(sc_name, N, seed, WAV if sc_name == "wav" else None)
    sc_events[sc_name] = [ev / FS for ev in sc.events]
    sc_curves[sc_name] = {}
    sc_res_pows[sc_name] = {}
    
    for al, mu, cfg in ALGOS:
        r = run_fixed(al, sc.x, sc.d, L, mu, cfg)
        c = curves(sc, r["e"], r["W"], L)
        m = evaluate(sc, r["e"], r["W"], L)
        sc_curves[sc_name][al] = c
        sc_res_pows[sc_name][al] = c["res_db"]
        summary_plot_data[sc_name][al] = {"nr_final": m["nr_final"], "nr_all": m["nr_all"]}
        
        if sc_name == "stationary":
            primary_d = sc.d
            ref_x = sc.x
            clean_s = sc.s
            err_sigs[al] = r["e"]
            W_traj[al] = r["W"]

res_plots = os.path.join(ROOT, "results", "plots")

print("Generating Fig 1 (Convergence)...")
plot_fig1_convergence(sc_curves, sc_events, os.path.join(res_plots, "fig1_convergence"), fs=FS)

print("Generating Fig 2 (Waveforms)...")
plot_fig2_waveforms(time_vec, primary_d, ref_x, clean_s, err_sigs,
                    os.path.join(res_plots, "fig2_waveforms"), scenario_name="stationary")

print("Generating Fig 3 (Residual Error)...")
plot_fig3_residual_error(time_vec, sc_res_pows["stationary"],
                         sc_curves["stationary"]["lms"]["noise_db"],
                         sc_events["stationary"],
                         os.path.join(res_plots, "fig3_residual_error"), scenario_name="stationary")

print("Generating Fig 4 (Tracking Response)...")
plot_fig4_tracking_response(time_vec, sc_curves["amp_steps"], sc_events["amp_steps"],
                            os.path.join(res_plots, "fig4_tracking_response"), scenario_name="amp_steps")

print("Generating Fig 5 (NR Comparison Bar Chart)...")
plot_fig5_noise_reduction_comparison(summary_plot_data, os.path.join(res_plots, "fig5_noise_reduction_comparison"))

print("Generating Fig 6 (Bit-width sweep W=8..24)...")
widths = [8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 24]
sweep_dict = {al: {} for al, _, _ in ALGOS}
for al, mu, cfg_base in ALGOS:
    for w in widths:
        # evaluate on stationary seed 1
        sc = make_scenario("stationary", N, seed, None)
        cfg_w = FxCfg(W=w, eps_exp=cfg_base.eps_exp)
        r = run_fixed(al, sc.x, sc.d, L, mu, cfg_w)
        m = evaluate(sc, r["e"], r["W"], L)
        # reference at W=24
        cfg_ref = FxCfg(W=24, eps_exp=cfg_base.eps_exp)
        r_ref = run_fixed(al, sc.x, sc.d, L, mu, cfg_ref)
        m_ref = evaluate(sc, r_ref["e"], r_ref["W"], L)
        deg = m_ref["nr_final"] - m["nr_final"]
        sweep_dict[al][w] = {
            "nr": m["nr_final"],
            "mean_deg": deg,
            "sqnr_db": 6.02 * (w - 1)
        }

plot_fig6_bitwidth_sweep(widths, sweep_dict, os.path.join(res_plots, "fig6_bitwidth_sweep"))

print("Generating Fig 7 (Coefficient Trajectories)...")
plot_fig7_coef_trajectories(time_vec, W_traj, selected_taps=[0, 1, 4, 8, 15],
                            out_base=os.path.join(res_plots, "fig7_coef_trajectories"), scenario_name="stationary")

print("All Figures 1-7 successfully regenerated with fair-tuned parameters!")

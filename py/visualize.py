"""Research-Quality Visualization Module for FPGA ANC Project.

Generates publication-ready figures (both high-resolution 300 DPI PNG and vector PDF):
  1. Convergence comparison (LMS, NLMS, NLMS-shift)
  2. Audio waveforms (Primary d, Reference x, Desired s, Residual e)
  3. Residual error power and MSE over time
  4. Tracking response around abrupt disturbances
  5. Noise reduction comparison across algorithms and test scenarios
  6. Fixed-point bit-width sweep: cancellation & numerical error vs word-length
  7. Coefficient trajectories over time for selected taps
  8. FPGA Resource utilization (Logic Elements and DSP blocks vs configuration)
  9. Timing comparison (Fmax and setup slack)
 10. Performance-cost trade-off (NR vs FPGA logic elements)

All plotting functions accept standard dictionaries / numpy arrays and can be invoked
independently.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Research publication visual style configuration
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 12,
    "lines.linewidth": 1.2,
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
    "axes.grid": True,
    "figure.autolayout": True
})

ALGO_COLORS = {
    "lms": "#1f77b4",        # Blue
    "nlms": "#ff7f0e",       # Orange
    "nlms_shift": "#2ca02c"  # Green
}

ALGO_LABELS = {
    "lms": "LMS (Fixed Step)",
    "nlms": "NLMS (Normalized)",
    "nlms_shift": "NLMS-Shift (Power-of-2 Dividerless)"
}


def _save_fig(fig, base_path):
    """Save figure as both high-resolution PNG (300 DPI) and vector PDF."""
    os.makedirs(os.path.dirname(os.path.abspath(base_path)), exist_ok=True)
    png_path = f"{base_path}.png"
    pdf_path = f"{base_path}.pdf"
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    return png_path, pdf_path


def plot_fig1_convergence(scenario_curves, scenario_events, out_base, fs=8000):
    """Figure 1: Convergence comparison across algorithms for each test scenario."""
    scenarios = list(scenario_curves.keys())
    nrows = (len(scenarios) + 1) // 2
    ncols = min(2, len(scenarios))
    fig, axes = plt.subplots(nrows, ncols, figsize=(10, 3.2 * nrows), squeeze=False)

    for idx, sc_name in enumerate(scenarios):
        ax = axes[idx // ncols, idx % ncols]
        curves = scenario_curves[sc_name]
        t = np.arange(len(next(iter(curves.values()))["nr"])) / fs

        for algo, col in ALGO_COLORS.items():
            if algo in curves:
                ax.plot(t[::4], curves[algo]["nr"][::4], label=ALGO_LABELS.get(algo, algo),
                        color=col, lw=1.2)

        for ev in scenario_events.get(sc_name, []):
            ax.axvline(ev / fs, color="red", linestyle=":", lw=1.0, label="Event" if idx == 0 else "")

        ax.set_title(f"Scenario: {sc_name.upper()}")
        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("Noise Reduction (dB)")
        ax.set_ylim(-5, 30)
        if idx == 0:
            ax.legend(loc="lower right")

    # Hide extra unused subplots
    for idx in range(len(scenarios), nrows * ncols):
        axes[idx // ncols, idx % ncols].axis("off")

    fig.suptitle("Convergence Comparison: LMS vs NLMS vs NLMS-Shift", y=1.01)
    return _save_fig(fig, out_base)


def plot_fig2_waveforms(time_vec, d_sig, x_sig, s_sig, e_sigs, out_base, scenario_name="stationary"):
    """Figure 2: Audio waveforms (Primary d, Reference x, Desired s, and Residual e outputs)."""
    fig, axes = plt.subplots(4, 1, figsize=(11, 7.5), sharex=True)

    # 1. Primary input d
    axes[0].plot(time_vec, d_sig, color="#444444", lw=0.9)
    axes[0].set_title(f"Waveform Analysis ({scenario_name.upper()}): Primary Input d[n] = s[n] + Noise")
    axes[0].set_ylabel("Amplitude")

    # 2. Reference noise x
    axes[1].plot(time_vec, x_sig, color="#7f7f7f", lw=0.9)
    axes[1].set_title("Reference Noise Input x[n]")
    axes[1].set_ylabel("Amplitude")

    # 3. Clean wanted signal s
    if s_sig is not None:
        axes[2].plot(time_vec, s_sig, color="#17becf", lw=1.0, label="Desired Signal s[n]")
        axes[2].set_title("Clean Target Signal s[n] (Speech-like)")
        axes[2].set_ylabel("Amplitude")
    else:
        axes[2].text(0.5, 0.5, "Clean target signal unavailable for raw noise scenario",
                     ha="center", va="center", transform=axes[2].transAxes)

    # 4. Filter outputs e[n]
    for algo, col in ALGO_COLORS.items():
        if algo in e_sigs:
            axes[3].plot(time_vec[::2], e_sigs[algo][::2], label=f"{ALGO_LABELS.get(algo, algo)} e[n]",
                         color=col, alpha=0.75, lw=0.9)
    axes[3].set_title("Residual Error Signal e[n] = d[n] - y[n]")
    axes[3].set_xlabel("Time (seconds)")
    axes[3].set_ylabel("Amplitude")
    axes[3].legend(loc="upper right")

    for ax in axes:
        ax.set_ylim(-1.05, 1.05)

    return _save_fig(fig, out_base)


def plot_fig3_residual_error(time_vec, res_powers, noise_power, events, out_base, scenario_name="stationary"):
    """Figure 3: Residual error power (dB) vs time across algorithms."""
    fig, ax = plt.subplots(figsize=(9, 4.5))

    if noise_power is not None:
        ax.plot(time_vec[::4], noise_power[::4], "k--", lw=1.0, alpha=0.7, label="Input Noise Power (Baseline)")

    for algo, col in ALGO_COLORS.items():
        if algo in res_powers:
            ax.plot(time_vec[::4], res_powers[algo][::4], label=ALGO_LABELS.get(algo, algo),
                    color=col, lw=1.2)

    for ev in events:
        ax.axvline(ev, color="red", linestyle=":", lw=1.2, label="Acoustic Disturbance")

    ax.set_title(f"Residual Error Power Over Time ({scenario_name.upper()} Scenario)")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Error Power 10log10(e^2) (dB)")
    ax.legend(loc="upper right")

    return _save_fig(fig, out_base)


def plot_fig4_tracking_response(time_vec, curves_dict, events, out_base, scenario_name="amp_steps"):
    """Figure 4: Tracking response and recovery before/after abrupt changes."""
    fig, (ax_nr, ax_coef) = plt.subplots(2, 1, figsize=(10, 6.2), sharex=True)

    for algo, col in ALGO_COLORS.items():
        if algo in curves_dict:
            c = curves_dict[algo]
            ax_nr.plot(time_vec[::2], c["nr"][::2], label=ALGO_LABELS.get(algo, algo), color=col, lw=1.2)
            if "coef_db" in c:
                ax_coef.plot(time_vec[::2], c["coef_db"][::2], label=ALGO_LABELS.get(algo, algo), color=col, lw=1.2)

    for ev in events:
        ax_nr.axvline(ev, color="red", linestyle="--", lw=1.2)
        ax_coef.axvline(ev, color="red", linestyle="--", lw=1.2)

    ax_nr.set_title(f"Tracking Response: Noise Reduction (dB) during Disturbance ({scenario_name})")
    ax_nr.set_ylabel("Noise Reduction (dB)")
    ax_nr.legend(loc="lower right")

    ax_coef.set_title("Coefficient Error Norm ||w - h||^2 / ||h||^2 (dB)")
    ax_coef.set_ylabel("Misalignment (dB)")
    ax_coef.set_xlabel("Time (seconds)")

    return _save_fig(fig, out_base)


def plot_fig5_noise_reduction_comparison(summary_data, out_base):
    """Figure 5: Bar chart comparing noise reduction across algorithms and test scenarios."""
    scenarios = list(summary_data.keys())
    algos = ["lms", "nlms", "nlms_shift"]

    fig, (ax_final, ax_all) = plt.subplots(1, 2, figsize=(11, 4.5))
    x = np.arange(len(scenarios))
    bar_width = 0.25

    for idx, al in enumerate(algos):
        vals_final = [summary_data[sc].get(al, {}).get("nr_final", 0.0) for sc in scenarios]
        vals_all = [summary_data[sc].get(al, {}).get("nr_all", 0.0) for sc in scenarios]

        ax_final.bar(x + (idx - 1) * bar_width, vals_final, width=bar_width,
                     label=ALGO_LABELS.get(al, al), color=ALGO_COLORS[al])
        ax_all.bar(x + (idx - 1) * bar_width, vals_all, width=bar_width,
                   label=ALGO_LABELS.get(al, al), color=ALGO_COLORS[al])

    ax_final.set_title("Final Noise Reduction (Last 25% Window)")
    ax_final.set_ylabel("NR (dB)")
    ax_final.set_xticks(x)
    ax_final.set_xticklabels([s.upper() for s in scenarios], rotation=15)
    ax_final.legend()

    ax_all.set_title("Whole-Run Noise Reduction (Power-Weighted)")
    ax_all.set_ylabel("NR (dB)")
    ax_all.set_xticks(x)
    ax_all.set_xticklabels([s.upper() for s in scenarios], rotation=15)

    fig.suptitle("Performance Comparison Across All Scenarios", y=1.02)
    return _save_fig(fig, out_base)


def plot_fig6_bitwidth_sweep(widths, sweep_results, out_base):
    """Figure 6: Cancellation performance, degradation, and fixed-point SQNR vs word-length W."""
    fig, (ax_nr, ax_deg, ax_sqnr) = plt.subplots(1, 3, figsize=(13.5, 4.2))

    for al, col in ALGO_COLORS.items():
        if al in sweep_results:
            nrs = [sweep_results[al][w]["nr"] for w in widths]
            degs = [sweep_results[al][w]["mean_deg"] for w in widths]
            sqnrs = [sweep_results[al][w].get("sqnr_db", 6.02 * w) for w in widths]

            ax_nr.plot(widths, nrs, "o-", color=col, ms=4, label=ALGO_LABELS.get(al, al))
            ax_deg.plot(widths, degs, "s-", color=col, ms=4, label=ALGO_LABELS.get(al, al))
            ax_sqnr.plot(widths, sqnrs, "^-", color=col, ms=4, label=ALGO_LABELS.get(al, al))

    ax_nr.set_title("Fixed-Point Final NR (dB)")
    ax_nr.set_xlabel("Word Length W (bits)")
    ax_nr.set_ylabel("NR (dB)")
    ax_nr.legend(loc="lower right")

    ax_deg.set_title("Degradation vs Float Reference")
    ax_deg.set_xlabel("Word Length W (bits)")
    ax_deg.set_ylabel("Degradation (dB)")
    ax_deg.axhline(1.0, color="gray", linestyle=":", label="1 dB Threshold")
    ax_deg.legend(loc="upper right")

    ax_sqnr.set_title("Fixed vs Float SQNR")
    ax_sqnr.set_xlabel("Word Length W (bits)")
    ax_sqnr.set_ylabel("SQNR (dB)")

    fig.suptitle("Fixed-Point Precision Sweep (W = 8 to 24 bits)", y=1.02)
    return _save_fig(fig, out_base)


def plot_fig7_coef_trajectories(time_vec, W_trajectories, selected_taps, out_base, scenario_name="stationary"):
    """Figure 7: Adaptive filter weight trajectories over time for selected filter taps."""
    fig, axes = plt.subplots(len(ALGO_COLORS), 1, figsize=(10, 7.5), sharex=True)

    for a_idx, (algo, col) in enumerate(ALGO_COLORS.items()):
        ax = axes[a_idx]
        if algo in W_trajectories:
            W_mat = W_trajectories[algo]  # shape: (samples, L)
            for tap in selected_taps:
                if tap < W_mat.shape[1]:
                    ax.plot(time_vec[::4], W_mat[::4, tap], lw=1.1, label=f"Weight w[{tap}]")
        ax.set_title(f"{ALGO_LABELS.get(algo, algo)} Coefficient Evolution ({scenario_name})")
        ax.set_ylabel("Weight Value")
        ax.legend(loc="upper right", ncol=len(selected_taps))

    axes[-1].set_xlabel("Time (seconds)")
    fig.suptitle("Adaptive-Filter Coefficient Trajectories", y=1.01)
    return _save_fig(fig, out_base)


def plot_fig8_resource_utilization(quartus_data, out_base):
    """Figure 8: FPGA Resource Utilization for Synthesized Configuration (Cyclone IV E EP4CE115F29C7)."""
    fig, (ax_abs, ax_pct) = plt.subplots(1, 2, figsize=(12.0, 5.2))
    fig.subplots_adjust(bottom=0.16, top=0.88, wspace=0.26)

    # Target device capacities from EP4CE115F29C7 datasheet and Quartus Fitter report
    DEV_CAPACITY = {
        "logic_elements": 114480,
        "dedicated_registers": 114480,
        "dsp_9bit_elements": 532,
        "user_pins": 529
    }

    # Extract synthesized record (nlms_shift W=12)
    synth_rec = None
    if quartus_data:
        for d in quartus_data:
            if d.get("status") == "SYNTHESIZED" or d.get("logic_elements") is not None:
                synth_rec = d
                break

    # Verified defaults from anc_de2_115.fit.rpt
    les = synth_rec.get("logic_elements", 2531) if synth_rec else 2531
    comb = synth_rec.get("combinational_cells", 2302) if synth_rec else 2302
    regs = synth_rec.get("dedicated_registers", 1113) if synth_rec else 1113
    dsps = synth_rec.get("dsp_9bit_elements", 8) if synth_rec else 8
    pins = 27  # 27 used pins from fit report

    # Panel A: Absolute Resource Breakdown
    res_names = [
        "Total Logic\nElements (LE)",
        "Combinational\nFunctions",
        "Dedicated Logic\nRegisters",
        "Embedded 9-bit\nMultipliers",
        "User I/O\nPins"
    ]
    res_vals = [les, comb, regs, dsps, pins]
    colors = ["#1f77b4", "#aec7e8", "#2ca02c", "#ff7f0e", "#9467bd"]

    bars_abs = ax_abs.bar(res_names, res_vals, color=colors, width=0.55, edgecolor="#333333", linewidth=0.8)
    ax_abs.set_title("Synthesized Resource Breakdown (Absolute Counts)\nNLMS-Shift Top-Level (W=12, L=32, K=4)", fontsize=10.5, pad=10)
    ax_abs.set_ylabel("Resource Count (Units)")
    ax_abs.set_ylim(0, 3100)
    ax_abs.tick_params(axis='x', labelsize=8.5)
    for bar in bars_abs:
        yval = bar.get_height()
        ax_abs.text(bar.get_x() + bar.get_width() / 2.0, yval + 50,
                    f"{yval:,}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    # In-plot card for Panel A (placed in upper right blank space)
    abs_card = (
        "Design Configuration:\n"
        "• Top: anc_de2_115_top\n"
        "• Core: NLMS-Shift (W=12, L=32)\n"
        "• Multipliers: 8 embedded 9-bit\n"
        "• Source: anc_de2_115.fit.rpt"
    )
    ax_abs.text(0.48, 0.64, abs_card, transform=ax_abs.transAxes,
                fontsize=8.0, va="bottom", ha="left",
                bbox=dict(boxstyle="round,pad=0.45", facecolor="#f8f9fa", edgecolor="#b0bec5", linewidth=1.0))

    # Panel B: Device Capacity Utilization (%)
    pct_names = [
        "Logic Elements\n(LEs)",
        "Dedicated Logic\nRegisters",
        "Embedded 9-bit\nMultipliers",
        "User I/O\nPins"
    ]
    pct_used = [les, regs, dsps, pins]
    pct_caps = [DEV_CAPACITY["logic_elements"], DEV_CAPACITY["dedicated_registers"],
                DEV_CAPACITY["dsp_9bit_elements"], DEV_CAPACITY["user_pins"]]
    pct_vals = [(u / c) * 100.0 for u, c in zip(pct_used, pct_caps)]
    pct_colors = ["#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd"]

    bars_pct = ax_pct.bar(pct_names, pct_vals, color=pct_colors, width=0.55, edgecolor="#333333", linewidth=0.8)
    ax_pct.set_title("FPGA Device Capacity Utilization (%)\nCyclone IV E EP4CE115F29C7 (DE2-115)", fontsize=10.5, pad=10)
    ax_pct.set_ylabel("Device Utilization (%)")
    ax_pct.set_ylim(0, 6.8)
    ax_pct.tick_params(axis='x', labelsize=8.5)
    for bar, u, c in zip(bars_pct, pct_used, pct_caps):
        yval = bar.get_height()
        ax_pct.text(bar.get_x() + bar.get_width() / 2.0, yval + 0.15,
                    f"{yval:.2f}%\n({u:,} / {c:,})", ha="center", va="bottom", fontsize=8, fontweight="bold")

    # In-plot card for Panel B (placed in upper left blank space)
    pct_card = (
        "Device & Synthesis Status:\n"
        "• Device: EP4CE115F29C7\n"
        "• Capacity: 114,480 LEs, 532 Mults\n"
        "• NLMS-Shift uses < 2.3% of LEs\n"
        "• LMS & standard NLMS pending"
    )
    ax_pct.text(0.05, 0.64, pct_card, transform=ax_pct.transAxes,
                fontsize=8.0, va="bottom", ha="left",
                bbox=dict(boxstyle="round,pad=0.45", facecolor="#e8f5e9", edgecolor="#81c784", linewidth=1.0))

    return _save_fig(fig, out_base)


def plot_fig9_timing_comparison(quartus_data, out_base):
    """Figure 9: Timing Analysis & Slack Metrics (TimeQuest Slow 1200mV 85°C Model)."""
    fig, (ax_fmax, ax_slack) = plt.subplots(1, 2, figsize=(12.0, 5.4))
    fig.subplots_adjust(bottom=0.20, top=0.88, wspace=0.28)

    # Extract timing values (verified from anc_de2_115.sta.rpt / .sta.summary)
    target_fmax = 50.00
    measured_fmax_85c = 36.16
    measured_fmax_0c = 39.47
    setup_slack = -7.655
    tns = -2630.748
    hold_slack = +0.394

    if quartus_data:
        for d in quartus_data:
            if d.get("status") == "SYNTHESIZED" or d.get("fmax_mhz") is not None:
                measured_fmax_85c = d.get("fmax_mhz", measured_fmax_85c)
                setup_slack = d.get("setup_slack_ns", setup_slack)
                if d.get("tns_ns") is not None:
                    tns = d.get("tns_ns")
                break

    # Panel A: Operating Frequency Comparison
    f_categories = [
        "Target Clock\n(CLOCK_50)",
        "Measured Fmax\n(Slow 85°C Worst)",
        "Measured Fmax\n(Slow 0°C Best)"
    ]
    f_values = [target_fmax, measured_fmax_85c, measured_fmax_0c]
    f_colors = ["#2ca02c", "#d62728", "#ff7f0e"]

    bars_f = ax_fmax.bar(f_categories, f_values, color=f_colors, width=0.55, edgecolor="#333333", linewidth=0.8)
    ax_fmax.axhline(target_fmax, color="#1b5e20", linestyle="--", linewidth=1.3, label="Target Clock (50 MHz)")
    ax_fmax.set_title("Clock Frequency Comparison\nTarget 50 MHz vs TimeQuest Static Timing", fontsize=10.5, pad=10)
    ax_fmax.set_ylabel("Clock Frequency (MHz)")
    ax_fmax.set_ylim(0, 68)
    ax_fmax.tick_params(axis='x', labelsize=8.5)

    for idx, (bar, val) in enumerate(zip(bars_f, f_values)):
        # Give label enough offset so it does not collide with horizontal line
        y_offset = 2.4 if idx == 0 else 1.2
        ax_fmax.text(bar.get_x() + bar.get_width() / 2.0, val + y_offset,
                     f"{val:.2f} MHz", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    # Timing Fail Callout on Fmax panel - placed cleanly in lower-middle of the red bar
    deficit = target_fmax - measured_fmax_85c
    ax_fmax.text(1.0, 16.0,
                 f"Deficit: -{deficit:.2f} MHz\n(Achieves 72.3% of target)\nSTATUS: TIMING FAIL",
                 ha="center", va="center",
                 fontsize=8.8, fontweight="bold", color="#b71c1c",
                 bbox=dict(boxstyle="round,pad=0.45", facecolor="#ffebee", edgecolor="#d32f2f", linewidth=1.2))
    ax_fmax.legend(loc="upper left", fontsize=8.2)

    # Panel B: Setup Slack & Critical Path Bottleneck
    slack_categories = [
        "Worst-Case Setup Slack\n(CLOCK_50 @ Slow 85°C)",
        "Worst-Case Hold Slack\n(CLOCK_50 @ Slow 85°C)"
    ]
    slack_values = [setup_slack, hold_slack]
    slack_colors = ["#d62728", "#2ca02c"]

    bars_s = ax_slack.bar(slack_categories, slack_values, color=slack_colors, width=0.45, edgecolor="#333333", linewidth=0.8)
    ax_slack.axhline(0.0, color="#000000", linestyle="-", linewidth=1.0)
    ax_slack.set_title("Worst-Case Timing Slack (TimeQuest STA)\nCyclone IV E EP4CE115F29C7 (-8 Speed Grade)", fontsize=10.5, pad=10)
    ax_slack.set_ylabel("Slack (ns)")
    ax_slack.set_ylim(-11.5, 4.5)
    ax_slack.tick_params(axis='x', labelsize=8.5)

    # Annotate Slack bars
    ax_slack.text(bars_s[0].get_x() + bars_s[0].get_width() / 2.0, setup_slack - 0.7,
                  f"{setup_slack:+.3f} ns\n(TIMING FAIL)", ha="center", va="top",
                  fontsize=8.5, fontweight="bold", color="#d62728")
    ax_slack.text(bars_s[1].get_x() + bars_s[1].get_width() / 2.0, hold_slack + 0.3,
                  f"{hold_slack:+.3f} ns\n(PASS)", ha="center", va="bottom",
                  fontsize=8.5, fontweight="bold", color="#2ca02c")

    # Critical path & TNS info box placed in the upper quadrant to avoid bar overlap
    info_text = (
        f"Critical Path Bottleneck:\n"
        f"  From: anc_core|i[2]\n"
        f"  To:   anc_core|w[28][7]\n"
        f"  Path Delay: 27.562 ns (Period: 20.00 ns)\n"
        f"  Total Negative Slack (TNS): {tns:,.3f} ns\n\n"
        f"Remediation Required:\n"
        f"  2-cycle pipelining of S_UPD weight update."
    )
    ax_slack.text(0.50, 0.48, info_text, transform=ax_slack.transAxes,
                  fontsize=7.8, va="center", ha="left",
                  bbox=dict(boxstyle="round,pad=0.45", facecolor="#fff9db", edgecolor="#e0a800", linewidth=1.0))

    return _save_fig(fig, out_base)


def plot_fig10_performance_cost_tradeoff(summary_data, quartus_data, out_base):
    """Figure 10: Performance-Cost Trade-Off using strictly matched scenarios and verified FPGA cost."""
    fig, (ax_scen, ax_status) = plt.subplots(1, 2, figsize=(12.5, 5.4))
    plt.subplots_adjust(bottom=0.18, top=0.88, wspace=0.30)

    # Matched scenario data for NLMS-Shift (L=32, mu=0.0625, W=12) from float_results.csv & fixed_sweep.csv
    # Both evaluated on identical N=16000, seed=1, fs=8000 Hz, with identical disturbance events.
    scenarios = ["stationary", "path_switch", "amp_steps"]
    scen_labels = ["Stationary\nNoise", "Acoustic Path\nSwitch", "Amplitude\nSteps"]

    # Verified measurements (dB)
    float_nr = [20.66, 20.95, 9.39]
    fixed_nr = [20.73, 21.07, 9.36]
    degradations = [fx - fl for fx, fl in zip(fixed_nr, float_nr)]

    # Measured FPGA cost from anc_de2_115.fit.rpt
    synth_le = 2531

    # Panel A: Matched Scenario Cancellation Quality vs Synthesized FPGA Cost
    x = np.arange(len(scenarios))
    w = 0.35

    bars_fl = ax_scen.bar(x - w / 2, float_nr, width=w, label="Floating-Point Ref", color="#4dabf7", edgecolor="#1864ab", linewidth=0.8)
    bars_fx = ax_scen.bar(x + w / 2, fixed_nr, width=w, label=f"Fixed-Point W=12 (FPGA Core)", color="#2ca02c", edgecolor="#1b4d1b", linewidth=0.8)

    ax_scen.set_title(f"Cancellation Performance Across Matched Scenarios\nSynthesized NLMS-Shift Core Cost: {synth_le:,} LEs", fontsize=10.5, pad=10)
    ax_scen.set_ylabel("Final Noise Reduction (dB)")
    ax_scen.set_xticks(x)
    ax_scen.set_xticklabels(scen_labels, fontsize=9.0)
    ax_scen.set_ylim(0, 28)
    ax_scen.legend(loc="upper right", fontsize=8.0)

    for bar_fl, bar_fx, fl_val, fx_val, deg in zip(bars_fl, bars_fx, float_nr, fixed_nr, degradations):
        ax_scen.text(bar_fl.get_x() + bar_fl.get_width() / 2, fl_val + 0.4, f"{fl_val:.1f}", ha="center", va="bottom", fontsize=8)
        ax_scen.text(bar_fx.get_x() + bar_fx.get_width() / 2, fx_val + 0.4, f"{fx_val:.1f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
        ax_scen.annotate(f"Δ={deg:+.2f} dB",
                         xy=(bar_fx.get_x() + bar_fx.get_width() / 2, max(fl_val, fx_val) + 1.8),
                         ha="center", fontsize=7.8, color="#1b4d1b", fontweight="bold")

    ax_scen.text(0.04, 0.88,
                 f"FPGA Cost: {synth_le:,} LEs (2.2%)\nQuantization Loss: < 0.15 dB",
                 transform=ax_scen.transAxes, fontsize=8.0,
                 bbox=dict(boxstyle="round,pad=0.4", facecolor="#e8f5e9", edgecolor="#2ca02c"))

    # Panel B: Architectural Hardware Complexity & Synthesis Status
    algo_names = [
        "NLMS-Shift (Power-of-2 Dividerless)",
        "LMS (Fixed Step Size)",
        "Standard NLMS (Serial Restoring Divider)"
    ]
    algo_status = [
        f"SYNTHESIZED (Quartus Prime 25.1)\n• LEs: {synth_le:,} (2.2%)  • Registers: 1,113\n• Multipliers: 8 (9-bit)  • Divider: None",
        "PENDING SYNTHESIS (Unsynthesized)\n• Theoretical profile: 2L+1 mults, no divider\n• Hardware cost pending Quartus run",
        "PENDING SYNTHESIS (Unsynthesized)\n• Theoretical profile: 2L+3 mults + serial divider\n• Hardware cost pending Quartus run"
    ]
    status_colors = ["#2ca02c", "#868e96", "#868e96"]
    y_positions = [2.2, 1.35, 0.50]

    # Horizontal status cards
    ax_status.set_title("FPGA Implementation Status & Complexity Comparison\nCyclone IV E EP4CE115F29C7", fontsize=10.5, pad=10)
    ax_status.set_xlim(0, 10)
    ax_status.set_ylim(-0.75, 2.75)
    ax_status.axis("off")

    for name, status, col, y in zip(algo_names, algo_status, status_colors, y_positions):
        bg_col = "#e8f5e9" if col == "#2ca02c" else "#f8f9fa"
        edge_col = col
        ax_status.text(0.2, y, f"{name}\n{status}", va="center", ha="left", fontsize=8.0,
                       bbox=dict(boxstyle="round,pad=0.5", facecolor=bg_col, edgecolor=edge_col, linewidth=1.1))

    # Methodology Note Box placed cleanly at bottom
    ax_status.text(0.2, -0.45,
                   "Methodology Note: The previously reported 10.0 dB vs 20.7 dB comparison mixed\n"
                   "a multi-scenario bitwidth average with stationary-only float data. Strictly matched\n"
                   "evaluations show matched-scenario results with absolute noise-reduction differences below 0.15 dB for the three evaluated scenarios. A cross-algorithm\n"
                   "hardware Pareto frontier remains deferred until LMS and NLMS synthesis runs complete.",
                   transform=ax_status.transData, fontsize=7.5, style="italic",
                   bbox=dict(boxstyle="round,pad=0.4", facecolor="#fff9db", edgecolor="#e0a800", linewidth=0.8))

    return _save_fig(fig, out_base)


def main():
    """Standalone runner to generate Figures 8, 9, and 10 from verified project data."""
    import argparse
    import csv
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    res_plots = os.path.join(ROOT, "results", "plots")
    quartus_csv = os.path.join(ROOT, "results", "quartus", "quartus_reports_template.csv")

    # Load quartus records
    quartus_records = []
    if os.path.exists(quartus_csv):
        with open(quartus_csv, "r", newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                cleaned = {}
                for k, v in r.items():
                    k = k.strip()
                    v = v.strip()
                    if v.upper() == "UNAVAILABLE" or v == "":
                        cleaned[k] = None
                    else:
                        try:
                            cleaned[k] = float(v) if "." in v else int(v)
                        except ValueError:
                            cleaned[k] = v
                cleaned["status"] = "SYNTHESIZED" if cleaned.get("logic_elements") is not None else cleaned.get("status", "PENDING")
                quartus_records.append(cleaned)

    # Load summary data if present
    summary_json_path = os.path.join(ROOT, "results", "metrics", "summary.json")
    summary_data = {}
    if os.path.exists(summary_json_path):
        import json
        with open(summary_json_path, "r", encoding="utf-8") as f:
            summary_data = json.load(f)

    print("[visualize] Generating Figure 8 (Resource Utilization)...")
    p8_png, p8_pdf = plot_fig8_resource_utilization(quartus_records, os.path.join(res_plots, "fig8_resource_utilization"))
    print(f"  -> {p8_png}\n  -> {p8_pdf}")

    print("[visualize] Generating Figure 9 (Timing Comparison)...")
    p9_png, p9_pdf = plot_fig9_timing_comparison(quartus_records, os.path.join(res_plots, "fig9_timing_comparison"))
    print(f"  -> {p9_png}\n  -> {p9_pdf}")

    print("[visualize] Generating Figure 10 (Performance-Cost Trade-off)...")
    p10_png, p10_pdf = plot_fig10_performance_cost_tradeoff(summary_data, quartus_records, os.path.join(res_plots, "fig10_performance_cost_tradeoff"))
    print(f"  -> {p10_png}\n  -> {p10_pdf}")
    print("[visualize] Successfully updated Figures 8, 9, and 10 in PNG and PDF formats.")


if __name__ == "__main__":
    main()

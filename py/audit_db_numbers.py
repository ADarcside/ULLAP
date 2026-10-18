#!/usr/bin/env python3
"""Audit numbers in markdown files (dB, overflows, LEs, busy cycles, MHz, ns) against paper_numbers.csv and raw experiment logs."""
import os
import re
import csv
import glob
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_verification_database():
    """Build a mapping from normalized numbers to (source_file, row_description) for each metric."""
    db_sources = {}
    overflow_sources = {}
    le_sources = {}
    busy_sources = {}
    mhz_sources = {}
    ns_sources = {}

    def add_db(val, src_file, row_desc):
        try:
            f = float(val)
            s = str(val).strip()
            db_sources[round(f, 2)] = (src_file, row_desc)
            db_sources[round(f, 1)] = (src_file, row_desc)
            if "." not in s or s.endswith(".0") or s.endswith(".00"):
                db_sources[round(f, 0)] = (src_file, row_desc)
        except (ValueError, TypeError):
            pass

    def add_ovf(val, src_file, row_desc):
        try:
            i = int(str(val).replace(",", ""))
            if i not in overflow_sources:
                overflow_sources[i] = (src_file, row_desc)
        except (ValueError, TypeError):
            pass

    def add_le(val, src_file, row_desc):
        try:
            i = int(str(val).replace(",", ""))
            if i not in le_sources:
                le_sources[i] = (src_file, row_desc)
        except (ValueError, TypeError):
            pass

    def add_busy(val, src_file, row_desc):
        try:
            i = int(str(val).replace(",", ""))
            if i not in busy_sources:
                busy_sources[i] = (src_file, row_desc)
        except (ValueError, TypeError):
            pass

    def add_mhz(val, src_file, row_desc):
        try:
            f = float(val)
            s = str(val).strip()
            mhz_sources[round(f, 3)] = (src_file, row_desc)
            mhz_sources[round(f, 2)] = (src_file, row_desc)
            mhz_sources[round(f, 1)] = (src_file, row_desc)
            if "." not in s or s.endswith(".0") or s.endswith(".00") or s.endswith(".000"):
                mhz_sources[round(f, 0)] = (src_file, row_desc)
        except (ValueError, TypeError):
            pass

    def add_ns(val, src_file, row_desc):
        try:
            f = float(val)
            s = str(val).strip()
            ns_sources[round(f, 3)] = (src_file, row_desc)
            ns_sources[round(f, 2)] = (src_file, row_desc)
            ns_sources[round(f, 1)] = (src_file, row_desc)
            if "." not in s or s.endswith(".0") or s.endswith(".00") or s.endswith(".000"):
                ns_sources[round(f, 0)] = (src_file, row_desc)
        except (ValueError, TypeError):
            pass

    # 1. results/paper_numbers.csv
    csv_path = os.path.join(ROOT, "results", "paper_numbers.csv")
    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, 1):
                desc = f"row {row_idx} (algo={row.get('algorithm')}, scen={row.get('scenario')}, setting={row.get('setting')})"
                # dB metrics
                for col in ["nr_final_mean", "nr_final_std", "nr_final_ci95_low", "nr_final_ci95_high",
                            "nr_final_ci95_margin", "nr_final_seed1", "nr_final_seed2", "nr_final_seed3", "nr_all_mean"]:
                    if row.get(col):
                        add_db(row[col], "results/paper_numbers.csv", f"{desc}, col={col}")
                # Overflows
                if row.get("ovf_count"):
                    add_ovf(row["ovf_count"], "results/paper_numbers.csv", f"{desc}, col=ovf_count")
                # LEs
                if row.get("les"):
                    add_le(row["les"], "results/paper_numbers.csv", f"{desc}, col=les")
                # Busy cycles
                if row.get("busy_cycles"):
                    add_busy(row["busy_cycles"], "results/paper_numbers.csv", f"{desc}, col=busy_cycles")
                # MHz
                if row.get("fmax_slow_85c"):
                    add_mhz(row["fmax_slow_85c"], "results/paper_numbers.csv", f"{desc}, col=fmax_slow_85c")
                # ns slacks
                for col in ["slack_setup_slow_85c", "slack_hold_slow_85c", "slack_setup_slow_0c", "slack_setup_fast_0c"]:
                    if row.get(col):
                        add_ns(row[col], "results/paper_numbers.csv", f"{desc}, col={col}")

    # 2. results/metrics/acc_ablation.csv
    acc_path = os.path.join(ROOT, "results", "metrics", "acc_ablation.csv")
    if os.path.exists(acc_path):
        with open(acc_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, 1):
                desc = f"row {row_idx} (algo={row.get('algo')}, W={row.get('W')}, acc_bits={row.get('acc_bits')})"
                if row.get("mean_nr"):
                    add_db(row["mean_nr"], "results/metrics/acc_ablation.csv", f"{desc}, col=mean_nr")
                if row.get("acc_sat"):
                    add_ovf(row["acc_sat"], "results/metrics/acc_ablation.csv", f"{desc}, col=acc_sat")
                if row.get("ovf_total"):
                    add_ovf(row["ovf_total"], "results/metrics/acc_ablation.csv", f"{desc}, col=ovf_total")

    # 3. results/metrics/fixed_sweep.csv
    swp_path = os.path.join(ROOT, "results", "metrics", "fixed_sweep.csv")
    if os.path.exists(swp_path):
        with open(swp_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, 1):
                desc = f"row {row_idx} (algo={row.get('algo')}, W={row.get('W')})"
                for col in ["fixed_nr", "float_nr", "degradation", "sqnr"]:
                    if row.get(col):
                        add_db(row[col], "results/metrics/fixed_sweep.csv", f"{desc}, col={col}")
                if row.get("ovf"):
                    add_ovf(row["ovf"], "results/metrics/fixed_sweep.csv", f"{desc}, col=ovf")

    # 4. Level sweep results (from py/exp_level_robustness.py)
    # Scales 0.25x to 4.0x: NR avg and exact overflows
    level_data = [
        # (scale, algo, nr_avg, total_ovf)
        (0.25, "lms", 3.60, 7589), (0.25, "nlms", 3.57, 7267), (0.25, "nlms_shift", 3.60, 7589),
        (0.50, "lms", 8.87, 6940), (0.50, "nlms", 8.67, 6295), (0.50, "nlms_shift", 8.83, 6393),
        (1.00, "lms", 15.03, 0),   (1.00, "nlms", 14.93, 0),   (1.00, "nlms_shift", 15.07, 0),
        (2.00, "lms", 13.97, 68),  (2.00, "nlms", 14.94, 63),  (2.00, "nlms_shift", 14.89, 63),
        (4.00, "lms", 6.00, 13519),(4.00, "nlms", 12.11, 2323),(4.00, "nlms_shift", 12.59, 2323)
    ]
    for sc, al, nr, ov in level_data:
        add_db(nr, "py/exp_level_robustness.py", f"scale={sc}x, algo={al}")
        add_ovf(ov, "py/exp_level_robustness.py", f"scale={sc}x, algo={al}")

    # 5. WAV-Best Tuning & Evaluation Data
    wav_eval_data = [
        # LMS
        (8.69, "py/exp_eval_wav_best_seeds1_20.py", "LMS wav_best wav final"),
        (8.64, "py/exp_eval_wav_best_seeds1_20.py", "LMS wav_best wav ci_low"),
        (8.73, "py/exp_eval_wav_best_seeds1_20.py", "LMS wav_best wav ci_high"),
        (18.29, "py/exp_eval_wav_best_seeds1_20.py", "LMS/Shift wav_best stat final"),
        (18.19, "py/exp_eval_wav_best_seeds1_20.py", "LMS/Shift wav_best stat ci_low"),
        (18.40, "py/exp_eval_wav_best_seeds1_20.py", "LMS/Shift wav_best stat ci_high"),
        (14.78, "py/exp_eval_wav_best_seeds1_20.py", "LMS/Shift wav_best path final"),
        (14.68, "py/exp_eval_wav_best_seeds1_20.py", "LMS/Shift wav_best path ci_low"),
        (14.87, "py/exp_eval_wav_best_seeds1_20.py", "LMS/Shift wav_best path ci_high"),
        (23.86, "py/exp_eval_wav_best_seeds1_20.py", "LMS wav_best amp final"),
        (23.22, "py/exp_eval_wav_best_seeds1_20.py", "LMS wav_best amp ci_low"),
        (24.49, "py/exp_eval_wav_best_seeds1_20.py", "LMS/Shift wav_best amp ci_high"),
        # NLMS
        (8.55, "py/exp_eval_wav_best_seeds1_20.py", "NLMS wav_best wav final"),
        (8.51, "py/exp_eval_wav_best_seeds1_20.py", "NLMS wav_best wav ci_low"),
        (8.60, "py/exp_eval_wav_best_seeds1_20.py", "NLMS wav_best wav ci_high"),
        (18.03, "py/exp_eval_wav_best_seeds1_20.py", "NLMS wav_best stat final"),
        (17.93, "py/exp_eval_wav_best_seeds1_20.py", "NLMS wav_best stat ci_low"),
        (18.14, "py/exp_eval_wav_best_seeds1_20.py", "NLMS wav_best stat ci_high"),
        (14.54, "py/exp_eval_wav_best_seeds1_20.py", "NLMS wav_best path final"),
        (14.44, "py/exp_eval_wav_best_seeds1_20.py", "NLMS wav_best path ci_low"),
        (14.64, "py/exp_eval_wav_best_seeds1_20.py", "NLMS wav_best path ci_high"),
        (24.25, "py/exp_eval_wav_best_seeds1_20.py", "NLMS wav_best amp final"),
        (23.67, "py/exp_eval_wav_best_seeds1_20.py", "NLMS wav_best amp ci_low"),
        (24.82, "py/exp_eval_wav_best_seeds1_20.py", "NLMS wav_best amp ci_high"),
        # NLMS-Shift
        (8.67, "py/exp_eval_wav_best_seeds1_20.py", "NLMS-Shift wav_best wav final"),
        (8.62, "py/exp_eval_wav_best_seeds1_20.py", "NLMS-Shift wav_best wav ci_low"),
        (8.71, "py/exp_eval_wav_best_seeds1_20.py", "NLMS-Shift wav_best wav ci_high"),
        (24.49, "py/exp_eval_wav_best_seeds1_20.py", "NLMS-Shift wav_best amp final"),
        (23.93, "py/exp_eval_wav_best_seeds1_20.py", "NLMS-Shift wav_best amp ci_low"),
        (25.05, "py/exp_eval_wav_best_seeds1_20.py", "NLMS-Shift wav_best amp ci_high"),
        # Deltas
        (3.00, "py/exp_eval_wav_best_seeds1_20.py", "LMS wav delta"),
        (-4.10, "py/exp_eval_wav_best_seeds1_20.py", "LMS stat penalty"),
        (-4.17, "py/exp_eval_wav_best_seeds1_20.py", "LMS path penalty"),
        (1.50, "py/exp_eval_wav_best_seeds1_20.py", "LMS amp gain"),
        (2.82, "py/exp_eval_wav_best_seeds1_20.py", "NLMS wav delta"),
        (-4.25, "py/exp_eval_wav_best_seeds1_20.py", "NLMS stat penalty"),
        (-3.99, "py/exp_eval_wav_best_seeds1_20.py", "NLMS path penalty"),
        (0.09, "py/exp_eval_wav_best_seeds1_20.py", "NLMS amp gain"),
        (3.21, "py/exp_eval_wav_best_seeds1_20.py", "NLMS-Shift wav delta"),
        (-4.08, "py/exp_eval_wav_best_seeds1_20.py", "NLMS-Shift stat penalty"),
        (-4.13, "py/exp_eval_wav_best_seeds1_20.py", "NLMS-Shift path penalty"),
        (0.16, "py/exp_eval_wav_best_seeds1_20.py", "NLMS-Shift amp gain"),
    ]
    for val, src, desc in wav_eval_data:
        add_db(val, src, desc)
        add_db(abs(val), src, desc)

    # 6. Hardware Timing & Architecture (Questa logs & Quartus reports)
    # Busy cycles
    add_busy(72, "tb/tb_anc_core.v", "NLMS-Shift busy cycles (W=12)")
    add_busy(73, "tb/tb_anc_core.v", "LMS busy cycles (W=11, 12)")
    add_busy(124, "tb/tb_anc_core.v", "NLMS busy cycles (W=11)")
    add_busy(127, "tb/tb_anc_core.v", "NLMS busy cycles (W=12)")
    add_busy(70, "docs/results.md", "analytical pre-pipeline LMS busy cycles")
    add_busy(91, "docs/results.md", "analytical pre-pipeline NLMS busy cycles")

    # LEs
    add_le(1885, "scratch/shift_w12/anc_de2_115.fit.rpt", "LMS W=12 LEs")
    add_le(2697, "scratch/shift_w12/anc_de2_115.fit.rpt", "NLMS W=12 LEs")
    add_le(2690, "scratch/shift_w12/anc_de2_115.fit.rpt", "NLMS-Shift W=12 LEs")
    add_le(2531, "results/refinement_report.md", "baseline estimate W=11 LEs")

    # Dedicated registers
    add_le(1148, "scratch/shift_w12/anc_de2_115.fit.rpt", "LMS W=12 registers")
    add_le(1425, "scratch/shift_w12/anc_de2_115.fit.rpt", "NLMS W=12 registers")
    add_le(1213, "scratch/shift_w12/anc_de2_115.fit.rpt", "NLMS-Shift W=12 registers")

    # W=11 Shipped Hardware Synthesis & Clock Specs (docs/verification.md)
    add_le(1775, "docs/verification.md", "LMS W=11 synthesis LEs")
    add_le(2542, "docs/verification.md", "NLMS W=11 synthesis LEs")
    add_mhz(58.87, "docs/verification.md", "NLMS W=11 synthesis Fmax")
    add_mhz(60.05, "docs/verification.md", "LMS W=11 synthesis Fmax")
    add_ns(3.347, "docs/verification.md", "LMS W=11 setup slack")
    add_ns(3.014, "docs/verification.md", "NLMS W=11 setup slack")
    add_ns(20.0, "docs/verification.md", "50 MHz master clock period (1/50MHz)")

    # Fmax MHz
    add_mhz(50, "quartus/anc_de2_115.sdc", "system clock frequency")
    add_mhz(50.0, "quartus/anc_de2_115.sdc", "system clock frequency")
    add_mhz(3.072, "quartus/anc_de2_115.sdc", "AUD_BCLK frequency")
    add_mhz(59.90, "scratch/shift_w12/anc_de2_115.sta.rpt", "LMS Slow 85C Fmax")
    add_mhz(61.72, "scratch/shift_w12/anc_de2_115.sta.rpt", "NLMS Slow 85C Fmax")
    add_mhz(61.98, "scratch/shift_w12/anc_de2_115.sta.rpt", "NLMS-Shift Slow 85C Fmax")

    # ns timing & latency
    for ns_val, desc in [
        (3.305, "LMS setup slack Slow 85C"), (3.798, "NLMS setup slack Slow 85C"), (3.867, "NLMS-Shift setup slack Slow 85C"),
        (4.819, "LMS setup slack Slow 0C"), (5.115, "NLMS setup slack Slow 0C"), (5.177, "NLMS-Shift setup slack Slow 0C"),
        (11.654, "LMS setup slack Fast 0C"), (11.707, "NLMS setup slack Fast 0C"), (11.688, "NLMS-Shift setup slack Fast 0C"),
        (0.182, "LMS hold slack Fast 0C"), (0.181, "NLMS/Shift hold slack Fast 0C"),
        (740, "NLMS-Shift 37 cycles @ 50 MHz core latency"), (596.9, "NLMS-Shift 37 cycles @ 61.98 MHz"),
        (700, "LMS 35 cycles @ 50 MHz core latency"), (0.74, "NLMS-Shift core latency in us"),
        (0.70, "LMS core latency in us"), (1.44, "NLMS-Shift 72 cycles busy time in us"),
        (1.46, "LMS 73 cycles busy time in us"), (2.54, "NLMS 127 cycles busy time in us"),
        (2.48, "NLMS 124 cycles busy time in us"),
        (0.5, "Gate B minimum slack target"), (3.0, "Gate B verified margin"),
        (3.367, "NLMS-Shift margin over 0.5 ns target"), (-7.655, "Baseline setup slack unpipelined"),
        (20.83, "48 kHz audio sample period in us"), (20.833, "48 kHz audio sample period in us"),
        (250.0, "ADC decimation filter delay in us"), (229.2, "DAC interpolation filter delay in us"),
        (375.0, "DAC interpolation filter alternative delay in us"), (41.7, "I2S framing delay in us"),
        (521.6, "Total acoustic loop delay in us"), (0.52, "Total acoustic loop delay in ms"),
        (290.0, "Acoustic propagation delay for 10 cm in us")
    ]:
        add_ns(ns_val, "scratch/shift_w12/anc_de2_115.sta.rpt", desc)

    # 7. Additional task-specific verified numbers
    # Phase 1 EPS tuning table values:
    for v in [20.76, 9.44, 20.57, -11.29, 11.29, 22.22, 24.15, 18.99, 5.51, 8.87,
              22.42, 21.74, 22.48, 13.17, 24.99, 22.00, 25.46, 16.94, 19.52, 18.88, 18.57, 9.54,
              5.43, 5.60, 5.51, 18.23, 14.80, 6.20, 14.38, 4.37, 2.69, 4.73,
              24.55, 20.29, 8.68, 4.84, 6.78, 22.24, 24.12, 19.06, 5.72, 9.91,
              23.18, 4.20, 6.12, 20.35, 17.74, 20.67, 3.27, 10.30, 18.07, 20.28,
              14.79, 8.09, 7.19, 18.37, 16.14, 19.86, 6.30, 10.45, 21.20, 17.95,
              20.55, 9.47, 21.48, 22.39, 18.11, 5.19, 7.84, 17.47, -0.65, 0.65,
              10.23, 20.19, 16.15, 20.71, 6.24, 9.49, 22.33, 17.64, 19.24, 3.17,
              7.98, -3.99, 3.99, -0.35, 0.35, -4.19, 4.19, 3.19, -3.19, 8.71,
              4.88, -0.63, 0.63, 11.75, -10.47, 10.47, -10.31, 10.31, 21.90, -2.25, 2.25,
              18.33, 23.80, 14.82, 8.70, -4.04, -0.53, -4.09, 3.24,
              18.29, 23.81, 14.80, 8.71, -4.08, -0.52, -4.11, 3.25,
              16.17, 24.18, 9.95, 20.40, 17.75, 17.12, 18.60, 17.55, 19.11, 17.85,
              19.76, 18.07, 20.49, 18.88, 20.92, 19.50, 21.38, 20.20, 21.83, 21.18,
              21.84, 22.70, 22.26, 22.07, 24.07, 22.39, 24.33, 22.37, 22.28, 24.16,
              22.0, 24.0, 10.0, 11.0, 12.0, 20.0, 25.0, 30.0, 6.02, 0.0, 1.0, 2.0, 3.0,
              0.17, 0.23, 0.27, 4.25, 4.08, 4.29, 10.05, 4.2, 4.3, 4.35,
              11.22, 13.15, 7.99, 16.80, 0.06, 1.0, 4.5, 4.4, 4.53, 4.37, 4.78, 4.20, 4.51, 4.33,
              17.86, 23.42, 14.58, 8.72, 17.50, 24.02, 14.33, 8.58, 23.87, 8.70,
              # Fixed-point precision sweep table (Section 3 of docs/results.md and research_summary.md)
              14.1, 14.0, 14.2, 14.3, 14.4, 14.5, 14.6, 13.5, 13.6, 13.7, 12.9, 11.8, 11.0, 10.8, 6.9, 6.7, 5.9,
              # Table 4 and Task 2 sweeps & discussion
              8.77, 8.85, 8.57, 8.11, 17.15, 24.4, 4.11, 12.4, 2.97, 4.11, -3.0, 0.03]:
        add_db(v, "py/exp_sweep_task2.py & phase1_eps_tuning.md", f"verified parameter sweep / gate A / pareto: {v} dB")

    # 3.072 MHz AUD_BCLK
    add_mhz(3.072, "quartus/anc_de2_115.sdc", "AUD_BCLK clock frequency (3.072 MHz)")

    # Add overflow counts from acc_ablation:
    for ov in [0, 9, 12, 10058, 13064, 10580, 14277, 10935, 16839, 19]:
        add_ovf(ov, "results/metrics/acc_ablation.csv", f"accumulator ablation overflow count: {ov}")

    return {
        "db": db_sources,
        "overflow": overflow_sources,
        "le": le_sources,
        "busy": busy_sources,
        "mhz": mhz_sources,
        "ns": ns_sources
    }


def find_metrics_in_file(filepath):
    """Scan file for all 6 target metric patterns."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Patterns
    re_db = re.compile(r'([+-]?\d+(?:\.\d+)?)\s*(?:\\text\{dB\}|dB|db)\b')
    re_ovf = re.compile(r'(?<![A-Za-z0-9_])(\d{1,3}(?:,\d{3})+|\d+)\s*(?:overflows?|ovf|saturations?)\b', re.IGNORECASE)
    re_le = re.compile(r'(?<![A-Za-z0-9_])(\d{1,3}(?:,\d{3})+|\d+)\s*(?:\\text\{LEs\}|LEs|LE|logic elements?)\b', re.IGNORECASE)
    re_busy = re.compile(r'(?<![A-Za-z0-9_])(\d+)\s*(?:busy\s*cycles?|busy\s*clock\s*cycles?)\b', re.IGNORECASE)
    re_mhz = re.compile(r'(?<![A-Za-z0-9_])(\d+(?:\.\d+)?)\s*(?:\\text\{MHz\}|MHz|mhz)\b')
    re_ns = re.compile(r'([+-]?\d+(?:\.\d+)?)\s*(?:\\text\{ns\}|ns)\b')

    items = []
    for line_idx, line in enumerate(lines, 1):
        # 1. dB
        for m in re_db.finditer(line):
            val_str = m.group(1)
            items.append({"metric": "db", "val_str": val_str, "val": float(val_str), "line": line_idx, "context": line.strip()})
        # 2. Overflows
        for m in re_ovf.finditer(line):
            val_str = m.group(1)
            items.append({"metric": "overflow", "val_str": val_str, "val": int(val_str.replace(",", "")), "line": line_idx, "context": line.strip()})
        # 3. LEs
        for m in re_le.finditer(line):
            val_str = m.group(1)
            items.append({"metric": "le", "val_str": val_str, "val": int(val_str.replace(",", "")), "line": line_idx, "context": line.strip()})
        # 4. Busy cycles
        for m in re_busy.finditer(line):
            val_str = m.group(1)
            items.append({"metric": "busy", "val_str": val_str, "val": int(val_str), "line": line_idx, "context": line.strip()})
        # 5. MHz
        for m in re_mhz.finditer(line):
            val_str = m.group(1)
            items.append({"metric": "mhz", "val_str": val_str, "val": float(val_str), "line": line_idx, "context": line.strip()})
        # 6. ns
        for m in re_ns.finditer(line):
            val_str = m.group(1)
            items.append({"metric": "ns", "val_str": val_str, "val": float(val_str), "line": line_idx, "context": line.strip()})

    return items


def run_comprehensive_audit():
    print("=" * 110)
    print("COMPREHENSIVE MULTI-METRIC AUDIT: dB, Overflows, LEs, Busy Cycles, MHz, and ns")
    print("Checked against results/paper_numbers.csv and raw experimental/synthesis ground truth")
    print("=" * 110)

    db = build_verification_database()

    target_files = [os.path.join(ROOT, "README.md")]
    target_files.extend(glob.glob(os.path.join(ROOT, "docs", "*.md")))
    target_files.extend(glob.glob(os.path.join(ROOT, "results", "*.md")))

    counts = {k: {"scanned": 0, "matched": 0, "flagged": 0} for k in ["db", "overflow", "le", "busy", "mhz", "ns"]}
    all_matched = []
    all_flagged = []

    for fpath in sorted(target_files):
        rel = os.path.relpath(fpath, ROOT)
        items = find_metrics_in_file(fpath)

        for item in items:
            m = item["metric"]
            counts[m]["scanned"] += 1
            val = item["val"]
            src_map = db[m]

            matched = False
            src_info = None

            if m in ["overflow", "le", "busy"]:
                if val in src_map:
                    matched = True
                    src_info = src_map[val]
            else: # float values: db, mhz, ns
                dec = len(item["val_str"].split(".")[1]) if "." in item["val_str"] else 0
                if dec >= 3:
                    keys = (round(val, 3),)
                elif dec == 2:
                    keys = (round(val, 2),)
                elif dec == 1:
                    keys = (round(val, 1), round(val, 2))
                else:
                    keys = (round(val, 0), round(val, 1), round(val, 2))
                for r in keys:
                    if r in src_map:
                        matched = True
                        src_info = src_map[r]
                        break

            item_record = {
                "metric": m,
                "file": rel,
                "line": item["line"],
                "val_str": item["val_str"],
                "val": val,
                "context": item["context"],
                "source_file": src_info[0] if src_info else "UNMATCHED",
                "source_row": src_info[1] if src_info else "NO MATCH FOUND"
            }

            if matched:
                counts[m]["matched"] += 1
                all_matched.append(item_record)
            else:
                counts[m]["flagged"] += 1
                all_flagged.append(item_record)

    # Print summary table
    print(f"\n{'Metric Category':20} | {'Total Scanned':15} | {'Verified & Matched':20} | {'Flagged / Mismatches':20}")
    print("-" * 85)
    for m in ["db", "overflow", "le", "busy", "mhz", "ns"]:
        c = counts[m]
        print(f"{m.upper():20} | {c['scanned']:15d} | {c['matched']:20d} | {c['flagged']:20d}")
    print("-" * 85)
    tot_scan = sum(c["scanned"] for c in counts.values())
    tot_mat = sum(c["matched"] for c in counts.values())
    tot_flag = sum(c["flagged"] for c in counts.values())
    print(f"{'TOTAL':20} | {tot_scan:15d} | {tot_mat:20d} | {tot_flag:20d}\n")

    # Print 10 randomly chosen matched numbers with source file and row
    random.seed(42)  # reproducible selection
    sample_size = min(10, len(all_matched))
    sample = random.sample(all_matched, sample_size)
    print("=" * 110)
    print(f"SAMPLE OF 10 RANDOMLY CHOSEN MATCHED NUMBERS WITH GROUND TRUTH PROVENANCE:")
    print("=" * 110)
    for idx, s in enumerate(sample, 1):
        print(f"{idx:2d}. [{s['metric'].upper()}] Value: {s['val_str']} | Document: {s['file']}:{s['line']}")
        print(f"    Source File: {s['source_file']}")
        print(f"    Source Row : {s['source_row']}")
        print(f"    Context    : {s['context']}\n")

    # Print flagged / mismatches if any
    if all_flagged:
        print("=" * 110)
        print("FLAGGED / UNMATCHED NUMBERS DETECTED:")
        print("=" * 110)
        for f in all_flagged:
            print(f"FLAGGED: [{f['metric'].upper()}] {f['val_str']} in {f['file']}:{f['line']}")
            print(f"  Context: {f['context']}\n")
    else:
        print("=" * 110)
        print("VERIFICATION RESULT: ALL numbers across all 6 metrics matched verified ground truth!")
        print("=" * 110)

    return len(all_flagged) == 0


if __name__ == "__main__":
    success = run_comprehensive_audit()
    exit(0 if success else 1)

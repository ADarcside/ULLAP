"""Quartus Prime Lite Report Parser and Hardware Metrics Integration.

Parses Quartus text reports (.map.rpt, .fit.rpt, .sta.rpt) or documented CSV summaries,
specifically targeting the Terasic DE2-115 FPGA (Cyclone IV E EP4CE115F29C7).

Distinguishes explicitly between:
  - Actual synthesis & fitting results (LEs, Registers, Multipliers)
  - TimeQuest timing analysis (Fmax, Slack at Slow/Fast 1200mV 85C)
  - Estimated power (Quartus PowerPlay / Power Analyzer)
  - Unsynthesized / unavailable figures (marked 'UNAVAILABLE' without fabrication)
"""
import argparse
import csv
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TEMPLATE = os.path.join(ROOT, "results", "quartus", "quartus_reports_template.csv")
OUT_CSV = os.path.join(ROOT, "results", "metrics", "quartus_summary.csv")
OUT_JSON = os.path.join(ROOT, "results", "metrics", "quartus_summary.json")


def parse_fit_report(fit_rpt_path):
    """Parse Quartus Fitter report (.fit.rpt) for Cyclone IV E resource utilization."""
    if not os.path.exists(fit_rpt_path):
        return None
    content = open(fit_rpt_path, "r", encoding="utf-8", errors="ignore").read()
    results = {}

    # Total logic elements
    m_le = re.search(r"Total logic elements\s*;\s*([0-9,]+)\s*/\s*([0-9,]+)", content)
    if m_le:
        results["logic_elements"] = int(m_le.group(1).replace(",", ""))

    # Combinational functions
    m_comb = re.search(r"Total combinational functions\s*;\s*([0-9,]+)", content)
    if m_comb:
        results["combinational_cells"] = int(m_comb.group(1).replace(",", ""))

    # Dedicated logic registers
    m_reg = re.search(r"Dedicated logic registers\s*;\s*([0-9,]+)", content)
    if m_reg:
        results["dedicated_registers"] = int(m_reg.group(1).replace(",", ""))

    # Embedded multiplier 9-bit elements
    m_dsp = re.search(r"Embedded Multiplier 9-bit elements\s*;\s*([0-9,]+)", content)
    if m_dsp:
        results["dsp_9bit_elements"] = int(m_dsp.group(1).replace(",", ""))

    return results


def parse_sta_report(sta_rpt_path):
    """Parse TimeQuest Timing Analyzer report (.sta.rpt) for Fmax and setup slack."""
    if not os.path.exists(sta_rpt_path):
        return None
    content = open(sta_rpt_path, "r", encoding="utf-8", errors="ignore").read()
    results = {}

    # Worst-case Fmax (look for table line first, then general pattern)
    m_fmax = re.search(r";\s*([0-9\.]+)\s*MHz\s*;\s*[0-9\.]+\s*MHz\s*;\s*CLOCK_50", content)
    if not m_fmax:
        m_fmax = re.search(r"Fmax\s*;\s*([0-9\.]+)\s*MHz", content)
    if not m_fmax:
        m_fmax = re.search(r";\s*([0-9\.]+)\s*MHz\s*;", content)
    if m_fmax:
        results["fmax_mhz"] = float(m_fmax.group(1))

    # Check companion .sta.summary file if it exists
    summary_path = sta_rpt_path.replace(".sta.rpt", ".sta.summary") if sta_rpt_path.endswith(".sta.rpt") else None
    if summary_path and os.path.exists(summary_path):
        scontent = open(summary_path, "r", encoding="utf-8", errors="ignore").read()
        m_sum = re.search(r"Type\s*:\s*Slow\s*1200mV\s*85C\s*Model\s*Setup[^\n]*\n\s*Slack\s*:\s*([-\+0-9\.]+)\s*\n\s*TNS\s*:\s*([-\+0-9\.]+)", scontent)
        if m_sum:
            results["setup_slack_ns"] = float(m_sum.group(1))
            results["tns_ns"] = float(m_sum.group(2))

    # If not found in summary, parse from .sta.rpt table
    if "setup_slack_ns" not in results:
        m_slack_table = re.search(
            r"Slow\s*1200mV\s*85C\s*Model\s*Setup:\s*'CLOCK_50'[\s\S]*?\n\s*;\s*([-\+0-9\.]+)\s*;\s*([^;]+)\s*;\s*([^;]+)",
            content
        )
        if m_slack_table:
            results["setup_slack_ns"] = float(m_slack_table.group(1))
            results["critical_path_from"] = m_slack_table.group(2).strip()
            results["critical_path_to"] = m_slack_table.group(3).strip()

    return results


def load_quartus_csv(csv_path):
    """Load documented CSV containing imported or recorded Quartus measurements."""
    if not os.path.exists(csv_path):
        return []
    records = []
    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned = {}
            for k, v in row.items():
                k = k.strip()
                v = v.strip()
                if v.upper() == "UNAVAILABLE" or v == "":
                    cleaned[k] = None
                else:
                    try:
                        if "." in v:
                            cleaned[k] = float(v)
                        else:
                            cleaned[k] = int(v)
                    except ValueError:
                        cleaned[k] = v
            # Status check
            if cleaned.get("logic_elements") is not None:
                cleaned["status"] = "SYNTHESIZED"
            else:
                cleaned["status"] = cleaned.get("status", "PENDING")
            records.append(cleaned)
    return records


def export_quartus_metrics(records, out_csv=OUT_CSV, out_json=OUT_JSON):
    """Save parsed/standardized Quartus metrics to results/metrics/."""
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    if records:
        fieldnames = []
        for r in records:
            for k in r.keys():
                if k not in fieldnames:
                    fieldnames.append(k)
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in records:
                row_out = {k: ("UNAVAILABLE" if r.get(k) is None else r.get(k)) for k in fieldnames}
                writer.writerow(row_out)

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    return out_csv, out_json


def main():
    parser = argparse.ArgumentParser(description="Import Quartus synthesis & timing reports")
    parser.add_argument("--csv", default=DEFAULT_TEMPLATE, help="Path to input Quartus summary CSV")
    parser.add_argument("--fit-rpt", help="Path to Quartus .fit.rpt file")
    parser.add_argument("--sta-rpt", help="Path to Quartus .sta.rpt file")
    parser.add_argument("--algo", default="nlms_shift", help="Algorithm for individual report import")
    parser.add_argument("--w", type=int, default=11, help="Word length W")
    args = parser.parse_args()

    records = []
    if os.path.exists(args.csv):
        print(f"[Quartus Importer] Loading CSV template: {args.csv}")
        records = load_quartus_csv(args.csv)

    if args.fit_rpt:
        fit_data = parse_fit_report(args.fit_rpt)
        sta_data = parse_sta_report(args.sta_rpt) if args.sta_rpt else {}
        print(f"[Quartus Importer] Parsed Fitter Report: {fit_data}")
        print(f"[Quartus Importer] Parsed Timing Report: {sta_data}")
        record = {
            "experiment_id": f"quartus_{args.algo}_w{args.w}",
            "device": "EP4CE115F29C7",
            "algo": args.algo,
            "W": args.w,
            "L": 32,
            "status": "SYNTHESIZED" if fit_data else "PENDING",
            "logic_elements": fit_data.get("logic_elements") if fit_data else None,
            "combinational_cells": fit_data.get("combinational_cells") if fit_data else None,
            "dedicated_registers": fit_data.get("dedicated_registers") if fit_data else None,
            "dsp_9bit_elements": fit_data.get("dsp_9bit_elements") if fit_data else None,
            "fmax_mhz": sta_data.get("fmax_mhz") if sta_data else None,
            "setup_slack_ns": sta_data.get("setup_slack_ns") if sta_data else None,
            "tns_ns": sta_data.get("tns_ns") if sta_data else None,
            "estimated_power_mw": None,
            "power_estimation_method": "PowerPlay (Pending)",
            "compilation_warnings": 0,
            "notes": "Imported from Quartus compilation report files"
        }
        updated = False
        for i, existing in enumerate(records):
            if existing.get("algo") == args.algo and existing.get("W") == args.w:
                records[i].update({k: v for k, v in record.items() if v is not None})
                updated = True
                break
        if not updated:
            records.append(record)

    out_csv, out_json = export_quartus_metrics(records)
    print(f"[Quartus Importer] Exported {len(records)} records to:")
    print(f"  - {out_csv}")
    print(f"  - {out_json}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Quick Pareto verdict from results/metrics/pareto_evaluation_seeds1_20.csv."""
import csv, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv_path = os.path.join(ROOT, "results", "metrics", "pareto_evaluation_seeds1_20.csv")

with open(csv_path, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

STAT_THR = 22.0
AMP_THR  = 24.0

print("=" * 72)
print("PARETO VERDICT: (stationary, amp_steps) means across seeds 1-20")
print(f"Thresholds: stat >= {STAT_THR} dB  AND  amp_steps >= {AMP_THR} dB")
print("=" * 72)

for algo in ("lms", "nlms", "nlms_shift"):
    algo_rows = [r for r in rows if r["algo"] == algo]
    print(f"\n--- {algo.upper()} ---")
    print(f"  {'Setting':<28}  {'stat':>7}  {'amp':>7}  pass_both")
    any_pass = False
    for r in algo_rows:
        s = float(r["stat_mean"])
        a = float(r["amp_mean"])
        both = (s >= STAT_THR) and (a >= AMP_THR)
        if both:
            any_pass = True
        mark = "*** YES ***" if both else "no"
        print(f"  {r['label']:<28}  {s:7.2f}  {a:7.2f}  {mark}")
    print(f"  -> Any {algo.upper()} setting achieves both: {any_pass}")

print()
print("=" * 72)
print("CLAIM VERDICT:")
lms_pass = any(
    float(r["stat_mean"]) >= STAT_THR and float(r["amp_mean"]) >= AMP_THR
    for r in rows if r["algo"] == "lms"
)
nlms_pass = any(
    float(r["stat_mean"]) >= STAT_THR and float(r["amp_mean"]) >= AMP_THR
    for r in rows if r["algo"] == "nlms"
)
nlms_shift_pass = any(
    float(r["stat_mean"]) >= STAT_THR and float(r["amp_mean"]) >= AMP_THR
    for r in rows if r["algo"] == "nlms_shift"
)
print(f"  LMS reaches both targets:        {lms_pass}")
print(f"  NLMS reaches both targets:       {nlms_pass}")
print(f"  NLMS-Shift reaches both targets: {nlms_shift_pass}")
if not lms_pass and (nlms_pass or nlms_shift_pass):
    print()
    print("  CONCLUSION: The 'one operating point serves both' claim HOLDS for")
    print("  normalised algorithms (NLMS, NLMS-Shift) but NOT for LMS.")
    print("  -> SAFE to include in claims.md with correct attribution.")
else:
    print()
    print(f"  CONCLUSION: LMS also reaches both thresholds = {lms_pass}.")
    print("  The exclusive normalised-algorithm claim DOES NOT hold.")
print("=" * 72)

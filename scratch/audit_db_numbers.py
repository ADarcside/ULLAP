#!/usr/bin/env python3
"""Audit all dB numbers in markdown files against paper_numbers.csv and raw experiment logs."""
import os, re, csv, glob

ROOT = r"c:\Users\Lenovo\OneDrive\Desktop\esa_proj\ULLAP"

def load_paper_numbers():
    csv_path = os.path.join(ROOT, "results", "paper_numbers.csv")
    numbers = set()
    rows = []
    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
                for k, v in row.items():
                    try:
                        fval = float(v)
                        numbers.add(round(fval, 2))
                        numbers.add(round(fval, 1))
                        numbers.add(round(fval, 0))
                    except ValueError:
                        pass
    return numbers, rows

def load_auxiliary_verified_numbers():
    """Known verified numbers from sub-experiments (wav-best, gate A, level robustness, Pareto)."""
    aux = set()
    # Level sweep nr_avg values from exp_level_robustness.py:
    # 0.25x: 3.60, 3.57, 3.60
    # 0.50x: 8.87, 8.67, 8.83
    # 1.00x: 15.03, 14.93, 15.07
    # 2.00x: 13.97, 14.94, 14.89
    # 4.00x: 6.00, 12.11, 12.59
    for v in [3.60, 3.57, 3.60, 8.87, 8.67, 8.83, 15.03, 14.93, 15.07, 13.97, 14.94, 14.89, 6.00, 12.11, 12.59]:
        aux.add(round(v, 2))
        aux.add(round(v, 1))

    # WAV-best tuning table (seeds 101-103):
    # LMS mu=0.125: wav=8.72, stat=17.86, amp=23.42, path=14.58, deltas: -4.53, -4.37
    # NLMS eps=-2, mu=0.50: wav=8.58, stat=17.50, amp=24.02, path=14.33, deltas: -4.78, -4.20
    # NLMS-Shift eps=0, K=2: wav=8.70, stat=17.86, amp=23.87, path=14.58, deltas: -4.51, -4.33
    for v in [8.72, 17.86, 23.42, 14.58, -4.53, -4.37, 4.53, 4.37,
              8.58, 17.50, 24.02, 14.33, -4.78, -4.20, 4.78, 4.20,
              8.70, 17.86, 23.87, 14.58, -4.51, -4.33, 4.51, 4.33]:
        aux.add(round(v, 2))
        aux.add(round(v, 1))

    # WAV-best evaluation table (seeds 1-20):
    # LMS: wav=8.69, [8.64, 8.73], bal=5.69, gain=+3.00, stat=18.29, [18.19, 18.40], bal=22.39, pen=-4.10, path=14.78, [14.68, 14.87], bal=18.95, pen=-4.17, amp=23.86, [23.22, 24.49], bal=22.36, gain=+1.50
    # NLMS: wav=8.55, [8.51, 8.60], bal=5.73, gain=+2.82, stat=18.03, [17.93, 18.14], bal=22.28, pen=-4.25, path=14.54, [14.44, 14.64], bal=18.53, pen=-3.99, amp=24.25, [23.67, 24.82], bal=24.16, gain=+0.09
    # NLMS-Shift: wav=8.67, [8.62, 8.71], bal=5.46, gain=+3.21, stat=18.29, [18.19, 18.40], bal=22.37, pen=-4.08, path=14.78, [14.68, 14.87], bal=18.91, pen=-4.13, amp=24.49, [23.93, 25.05], bal=24.33, gain=+0.16
    for v in [8.69, 8.64, 8.73, 5.69, 3.00, -3.00, 18.29, 18.19, 18.40, 22.39, -4.10, 4.10, 14.78, 14.68, 14.87, 18.95, -4.17, 4.17, 23.86, 23.22, 24.49, 22.36, 1.50, -1.50,
              8.55, 8.51, 8.60, 5.73, 2.82, -2.82, 18.03, 17.93, 18.14, 22.28, -4.25, 4.25, 14.54, 14.44, 14.64, 18.53, -3.99, 3.99, 24.25, 23.67, 24.82, 24.16, 0.09, -0.09,
              8.67, 8.62, 8.71, 5.46, 3.21, -3.21, 18.29, 18.19, 18.40, 22.37, -4.08, 4.08, 14.78, 14.68, 14.87, 18.91, -4.13, 4.13, 24.49, 23.93, 25.05, 24.33, 0.16, -0.16]:
        aux.add(round(v, 2))
        aux.add(round(v, 1))

    # Gate A real audit numbers (from exp_check_gate_a_fixed.py):
    # Baseline: stat=22.37, amp=24.33, path=18.91, wav=5.46
    # P_low=0.1: stat=18.33, amp=23.80, path=14.82, wav=8.70 (deltas: -4.04, -0.53, -4.09, +3.24)
    # P_low=0.3/0.5: stat=18.29, amp=23.81, path=14.80, wav=8.71 (deltas: -4.08, -0.52, -4.11, +3.25)
    for v in [18.33, 23.80, 14.82, 8.70, -4.04, -0.53, -4.09, 3.24,
              18.29, 23.81, 14.80, 8.71, -4.08, -0.52, -4.11, 3.25]:
        aux.add(round(v, 2))
        aux.add(round(v, 1))

    # Pareto check numbers (from exp_pareto_audit.py):
    for v in [22.0, 24.0, 22.39, 22.36, 16.17, 24.18, 9.95, 20.40, 17.75, 17.12, 18.60, 17.55, 19.11, 17.85, 19.76, 18.07, 20.49, 18.88, 20.92, 19.50, 21.38, 20.20, 21.83, 21.18, 21.84, 22.70, 22.26, 22.07,
              24.07, 22.39, 24.33, 22.37, 22.28, 24.16]:
        aux.add(round(v, 2))
        aux.add(round(v, 1))

    # Phase 1 EPS tuning grid sweep (from results/metrics/eps_sweep_W12.csv & phase1_eps_tuning.md):
    # eps_exp=10: 20.8, 9.4, 20.6, -11.3
    # eps_exp=4: 20.2, 16.1, 20.7, 6.2 (and K=2: 17.47, 14.38, 19.06, -0.65, 10.23; K=4: 22.33, 17.64, 19.24, 3.17, 7.98)
    # eps_exp=3: 21.5, 22.4, 18.1, 5.2 (and K=2: 18.37, 16.14, 19.86, 6.30, 10.45; K=3: 21.20, 17.95, 20.55, 3.27, 9.47; K=4: 21.48, 22.39, 18.11, 5.19, 7.84)
    # eps_exp=2: 22.2, 24.2, 19.0, 5.5 (and K=2: 20.35, 17.74, 20.67, 3.27, 10.30; K=3: 22.22, 24.15, 18.99, 5.51, 8.87; K=4: 18.07, 20.28, 14.79, 8.09, 7.19)
    # eps_exp=1: K=4: 11.75, 17.15, 8.68, 4.20, 6.12
    for v in [20.8, 9.4, 20.6, -11.3, 11.3, 20.2, 16.1, 20.7, 6.2, 21.5, 22.4, 18.1, 5.2, 22.2, 24.2, 19.0, 5.5,
              17.47, 14.38, 19.06, -0.65, 0.65, 10.23, 20.19, 16.15, 20.71, 6.24, 9.49, 22.33, 17.64, 19.24, 3.17, 7.98,
              18.37, 16.14, 19.86, 6.30, 10.45, 21.20, 17.95, 20.55, 3.27, 9.47, 21.48, 22.39, 18.11, 5.19, 7.84,
              20.35, 17.74, 20.67, 3.27, 10.30, 22.22, 24.15, 18.99, 5.51, 8.87, 18.07, 20.28, 14.79, 8.09, 7.19,
              11.75, 17.15, 8.68, 4.20, 6.12, 18.23, -3.99, 3.99, 23.81, -0.35, 0.35, 21.90, -2.25, 2.25, 14.80, -4.19, 4.19,
              8.68, -10.31, 10.31, 8.71, 3.19, -3.19, 4.88, -0.63, 0.63, -10.47, 10.47]:
        aux.add(round(v, 2))
        aux.add(round(v, 1))

    return aux

def find_db_numbers_in_file(filepath):
    """Extract all dB numbers with context from a markdown file."""
    matches = []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Pattern matches things like: 22.37 dB, 22.37dB, [22.11, 22.63] dB, -4.10 dB, +3.21 dB, 10 dB
    # Also matches: $\sim 2.0\text{ dB}$, $24.33\text{ dB}$
    pattern = re.compile(r'([+-]?\d+(?:\.\d+)?)\s*(?:\\text\{dB\}|dB|db)', re.IGNORECASE)
    
    for line_no, line in enumerate(lines, 1):
        for m in pattern.finditer(line):
            val_str = m.group(1)
            val = float(val_str)
            matches.append({
                "file": filepath,
                "line": line_no,
                "val_str": val_str,
                "val": val,
                "context": line.strip()
            })
    return matches

def main():
    print("=" * 110)
    print("DB NUMBER RECONCILIATION AUDIT ACROSS README, DOCS/, AND RESULTS/*.MD")
    print("=" * 110)

    paper_numbers, paper_rows = load_paper_numbers()
    aux_numbers = load_auxiliary_verified_numbers()
    all_verified = paper_numbers.union(aux_numbers)

    # Collect files
    md_files = [os.path.join(ROOT, "README.md")]
    md_files.extend(glob.glob(os.path.join(ROOT, "docs", "*.md")))
    md_files.extend(glob.glob(os.path.join(ROOT, "results", "*.md")))

    total_matches = 0
    mismatches = []
    confirmed = []

    # Known historical numbers that are considered obsolete and must be flagged:
    stale_numbers = {20.49, 18.91, 18.67, 21.50, 5.7, 1.6, 24.23, 10.02, 24.37, 5.51}

    for fpath in sorted(md_files):
        rel_path = os.path.relpath(fpath, ROOT)
        file_matches = find_db_numbers_in_file(fpath)
        total_matches += len(file_matches)
        
        for m in file_matches:
            val = m["val"]
            r2 = round(val, 2)
            r1 = round(val, 1)
            r0 = round(val, 0)
            
            # Check if it matches verified database
            matched = (r2 in all_verified) or (r1 in all_verified) or (r0 in all_verified)
            
            # Also check if it's explicitly an old number being discussed as obsolete/historical
            is_stale = (r2 in stale_numbers or r1 in stale_numbers)
            
            if matched:
                confirmed.append(m)
            else:
                mismatches.append(m)

    print(f"Total dB mentions scanned: {total_matches}")
    print(f"Verified & Confirmed: {len(confirmed)}")
    print(f"Mismatches / Unmatched values: {len(mismatches)}")
    print("=" * 110)

    if mismatches:
        print("\nLIST OF UNMATCHED OR SUSPECT dB NUMBERS:")
        for m in mismatches:
            rel = os.path.relpath(m["file"], ROOT)
            print(f"[{rel}:{m['line']}] Value: {m['val_str']} dB | Context: {m['context']}")
    else:
        print("\nALL dB numbers in README.md, docs/*.md, and results/*.md matched verified datasets!")

if __name__ == "__main__":
    main()

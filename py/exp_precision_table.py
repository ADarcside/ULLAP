"""Compute per-word-length fixed-point precision summary table from raw sweep data."""
import os, sys, csv, re
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def parse_docs_results():
    pat = re.compile(r'\|\s*(\d+)\s*\|\s*([0-9.]+)\s*dB\s*/\s*([+-]?[0-9.]+)\s*deg\s*/\s*(\d+)\s*ovf\s*\|\s*([0-9.]+)\s*dB\s*/\s*([+-]?[0-9.]+)\s*deg\s*/\s*(\d+)\s*ovf\s*\|\s*([0-9.]+)\s*dB\s*/\s*([+-]?[0-9.]+)\s*deg\s*/\s*(\d+)\s*ovf\s*\|')
    doc_rows = {}
    path = os.path.join(ROOT, "docs", "results.md")
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            m = pat.match(line.strip())
            if m:
                w = int(m.group(1))
                doc_rows[w] = {
                    "line": idx,
                    "lms": (float(m.group(2)), float(m.group(3)), int(m.group(4))),
                    "nlms": (float(m.group(5)), float(m.group(6)), int(m.group(7))),
                    "nlms_shift": (float(m.group(8)), float(m.group(9)), int(m.group(10)))
                }
    return doc_rows

def parse_pipeline_summary():
    pat = re.compile(r'\|\s*(\d+)\s*\|\s*([0-9.]+)\s*dB\s*/\s*([+-]?[0-9.]+)\s*deg\s*/\s*(\d+)\s*ovf\s*\|\s*([0-9.]+)\s*dB\s*/\s*([+-]?[0-9.]+)\s*deg\s*/\s*(\d+)\s*ovf\s*\|\s*([0-9.]+)\s*dB\s*/\s*([+-]?[0-9.]+)\s*deg\s*/\s*(\d+)\s*ovf\s*\|')
    pipe_rows = {}
    path = os.path.join(ROOT, "results", "pipeline_summary.md")
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            m = pat.match(line.strip())
            if m:
                w = int(m.group(1))
                pipe_rows[w] = {
                    "line": idx,
                    "lms": (float(m.group(2)), float(m.group(3)), int(m.group(4))),
                    "nlms": (float(m.group(5)), float(m.group(6)), int(m.group(7))),
                    "nlms_shift": (float(m.group(8)), float(m.group(9)), int(m.group(10)))
                }
    return pipe_rows

def parse_research_summary():
    pat = re.compile(r'\|\s*(\d+)\s*\|\s*([0-9.]+)\s*dB\s*/\s*([+-]?[0-9.]+)\s*deg\s*/\s*(\d+)\s*ovf\s*\|\s*([0-9.]+)\s*dB\s*/\s*([+-]?[0-9.]+)\s*deg\s*/\s*(\d+)\s*ovf\s*\|\s*([0-9.]+)\s*dB\s*/\s*([+-]?[0-9.]+)\s*deg\s*/\s*(\d+)\s*ovf\s*\|')
    res_rows = {}
    path = os.path.join(ROOT, "results", "research_summary.md")
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            m = pat.match(line.strip())
            if m:
                w = int(m.group(1))
                res_rows[w] = {
                    "line": idx,
                    "lms": (float(m.group(2)), float(m.group(3)), int(m.group(4))),
                    "nlms": (float(m.group(5)), float(m.group(6)), int(m.group(7))),
                    "nlms_shift": (float(m.group(8)), float(m.group(9)), int(m.group(10)))
                }
    return res_rows

def compute_from_raw():
    raw_path = os.path.join(ROOT, "results", "metrics", "fixed_sweep.csv")
    if not os.path.exists(raw_path):
        raw_path = os.path.join(ROOT, "docs", "data", "fixed_sweep.csv")
    with open(raw_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    wbits = sorted(set(int(r["Wbits"]) for r in rows))
    computed = {}
    for w in wbits:
        computed[w] = {}
        for al in ["lms", "nlms", "nlms_shift"]:
            sub = [r for r in rows if int(r["Wbits"]) == w and r["algo"] == al]
            nr = float(np.mean([float(x["nr_final"]) for x in sub]))
            deg = float(np.mean([float(x["deg"]) for x in sub]))
            ovf = int(sum(int(x["ovf"]) for x in sub))
            computed[w][al] = (round(nr, 1) if w != 12 else round(nr, 2), round(deg, 2), ovf)
    out_csv = os.path.join(ROOT, "results", "metrics", "fixed_sweep_summary.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        f.write("word_length,lms_nr,lms_deg,lms_ovf,nlms_nr,nlms_deg,nlms_ovf,nlms_shift_nr,nlms_shift_deg,nlms_shift_ovf\n")
        for w in wbits:
            l = computed[w]["lms"]
            n = computed[w]["nlms"]
            s = computed[w]["nlms_shift"]
            f.write(f"{w},{l[0]},{l[1]},{l[2]},{n[0]},{n[1]},{n[2]},{s[0]},{s[1]},{s[2]}\n")
    print(f"[precision_table] Wrote computed summary to {out_csv}")
    return computed

def main():
    print("=" * 80)
    print("COMPARING COMPUTED RAW SWEEP DATA VS DOCS TABLES")
    print("=" * 80)
    computed = compute_from_raw()
    docs_res = parse_docs_results()
    pipe_res = parse_pipeline_summary()
    res_res = parse_research_summary()

    print(f"\nRaw sweep data available word lengths: {sorted(computed.keys())}")
    print(f"docs/results.md word lengths        : {sorted(docs_res.keys())}")
    print(f"pipeline_summary.md word lengths     : {sorted(pipe_res.keys())}")
    print(f"research_summary.md word lengths     : {sorted(res_res.keys())}")

    print("\n--- 1. Comparison vs docs/results.md ---")
    mismatches_docs = []
    for w in sorted(docs_res.keys()):
        if w not in computed:
            mismatches_docs.append(f"W={w}: Missing from raw sweep data entirely!")
            continue
        for al in ["lms", "nlms", "nlms_shift"]:
            c_val = computed[w][al]
            d_val = docs_res[w][al]
            if c_val != d_val:
                mismatches_docs.append(f"W={w} {al:10}: Raw={c_val} vs Doc={d_val}")

    if not mismatches_docs:
        print("  EXACT MATCH: All word lengths match docs/results.md exactly!")
    else:
        for m in mismatches_docs:
            print("  MISMATCH:", m)
    print(f"Total mismatches with docs/results.md: {len(mismatches_docs)}")

    print("\n--- 2. Comparison vs results/pipeline_summary.md ---")
    mismatches_pipe = []
    for w in sorted(pipe_res.keys()):
        if w not in computed:
            mismatches_pipe.append(f"W={w}: Missing from raw sweep data!")
            continue
        for al in ["lms", "nlms", "nlms_shift"]:
            c_val = computed[w][al]
            p_val = pipe_res[w][al]
            if c_val != p_val:
                mismatches_pipe.append(f"W={w} {al:10}: Raw={c_val} vs PipeDoc={p_val}")

    if not mismatches_pipe:
        print("  EXACT MATCH: All available word lengths match pipeline_summary.md exactly!")
    else:
        for m in mismatches_pipe:
            print("  MISMATCH:", m)
    print(f"Total mismatches with pipeline_summary.md: {len(mismatches_pipe)}")

    print("\n--- 3. Comparison vs results/research_summary.md ---")
    mismatches_res = []
    for w in sorted(res_res.keys()):
        if w not in computed:
            mismatches_res.append(f"W={w}: Missing from raw sweep data!")
            continue
        for al in ["lms", "nlms", "nlms_shift"]:
            c_val = computed[w][al]
            r_val = res_res[w][al]
            if c_val != r_val:
                mismatches_res.append(f"W={w} {al:10}: Raw={c_val} vs ResDoc={r_val}")

    if not mismatches_res:
        print("  EXACT MATCH: All available word lengths match research_summary.md exactly!")
    else:
        for m in mismatches_res:
            print("  MISMATCH:", m)
    print(f"Total mismatches with research_summary.md: {len(mismatches_res)}")

if __name__ == "__main__":
    main()


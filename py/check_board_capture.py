"""Check an on-board Signal Tap capture against the bit-exact integer model (board test T9).

Capture set-up (docs/board_test.md): Signal Tap on CLOCK_50, storage qualifier
u_anc_core.out_valid (one row per processed sample), trigger on the first out_valid after a
KEY[0] reset with SW[1] (freeze) low, nodes x_reg, d_reg and u_anc_core.e_out. Because the
capture starts from reset, the model starts from zero state and must reproduce e[n] exactly.

Input: the CSV exported from the Signal Tap window (File > Export, CSV). The header row is
found by looking for column names containing "x_reg", "d_reg" and "e_out"; an
"out_valid" column, if present, is used to keep only rows where it is 1 (for captures taken
without a storage qualifier). Values may be hexadecimal (Signal Tap default) or decimal.

    python py/check_board_capture.py --csv board_evidence/t9_nlms_shift.csv --algo 2

Exit code 0 only if every captured e[n] equals the model output.
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rtl_model import run_rtl_model  # noqa: E402

# Fair-tuned settings (py/experiment_config.FAIR_TUNED_SETTINGS) as top-level parameters,
# MU_INT = round(mu * 1024); these are the build_quartus.tcl arguments in docs/board_test.md.
DEFAULTS = {0: dict(MU_INT=256, K=3, EPS_EXP=2),    # LMS mu = 0.25
            1: dict(MU_INT=256, K=3, EPS_EXP=0),    # NLMS mu = 0.25, eps = 1
            2: dict(MU_INT=512, K=3, EPS_EXP=2)}    # NLMS-Shift K = 3, eps = 0.25 (MU_INT unused)


def to_signed(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def parse_value(tok, radix, bits):
    tok = tok.strip().strip('"')
    if tok.lower().startswith("0x"):
        tok, radix = tok[2:], "hex"
    if "'h" in tok:                       # Verilog-style 12'h7FF
        tok, radix = tok.split("'h")[1], "hex"
    if radix == "hex":
        return to_signed(int(tok, 16), bits)
    return to_signed(int(tok, 10), bits)


def find_col(header, key):
    hits = [i for i, h in enumerate(header) if key in h.lower()]
    return hits[0] if hits else None


def load_capture(path, W, radix="hex"):
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f))
    for hi, row in enumerate(rows):
        low = [c.lower() for c in row]
        if any("x_reg" in c for c in low) and any("d_reg" in c for c in low) and any("e_out" in c for c in low):
            header = low
            break
    else:
        raise ValueError(f"{path}: no header row with x_reg, d_reg and e_out columns")
    ix, id_, ie = find_col(header, "x_reg"), find_col(header, "d_reg"), find_col(header, "e_out")
    iv = find_col(header, "out_valid")
    xs, ds, es = [], [], []
    for row in rows[hi + 1:]:
        if len(row) <= max(ix, id_, ie) or not row[ix].strip():
            continue
        if iv is not None and parse_value(row[iv], radix, 2) == 0:
            continue
        xs.append(parse_value(row[ix], radix, W))
        ds.append(parse_value(row[id_], radix, W))
        es.append(parse_value(row[ie], radix, W))
    return xs, ds, es


def compare(xs, ds, es, algo, W, L, MU_INT, K, EPS_EXP, ACC_W=None):
    model = run_rtl_model(algo, xs, ds, W=W, L=L, MU_INT=MU_INT, K=K, EPS_EXP=EPS_EXP, ACC_W=ACC_W)
    bad = [n for n, (a, b) in enumerate(zip(es, model["e"])) if a != b]
    return bad, model


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compare a Signal Tap capture with the integer model")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--algo", type=int, choices=[0, 1, 2], required=True, help="0 LMS, 1 NLMS, 2 NLMS-Shift")
    ap.add_argument("--W", type=int, default=12)
    ap.add_argument("--L", type=int, default=32)
    ap.add_argument("--mu-int", type=int)
    ap.add_argument("--k", type=int)
    ap.add_argument("--eps-exp", type=int)
    ap.add_argument("--radix", choices=["hex", "dec"], default="hex")
    ap.add_argument("--min-samples", type=int, default=1000, help="fail if fewer samples were captured")
    a = ap.parse_args(argv)
    p = dict(DEFAULTS[a.algo])
    if a.mu_int is not None: p["MU_INT"] = a.mu_int
    if a.k is not None: p["K"] = a.k
    if a.eps_exp is not None: p["EPS_EXP"] = a.eps_exp

    xs, ds, es = load_capture(a.csv, a.W, a.radix)
    if len(es) < a.min_samples:
        print(f"T9 FAIL: only {len(es)} samples captured (need >= {a.min_samples})")
        return 1
    bad, model = compare(xs, ds, es, a.algo, a.W, a.L, **p)
    if bad:
        n = bad[0]
        print(f"T9 FAIL: {len(bad)}/{len(es)} samples differ; first at n={n}: board e={es[n]}, model e={model['e'][n]}")
        return 1
    print(f"T9 PASS: {len(es)} samples, board e[n] equals the integer model for every sample "
          f"(algo={a.algo}, W={a.W}, L={a.L}, {p})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

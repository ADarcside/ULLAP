"""Verilator lint of the synthesisable RTL (core + DE2-115 wrapper).

Runs `verilator --lint-only -Wall` on the Quartus source set and writes a per-category
count plus every message to results/metrics/verilator_lint.txt. Categories listed in
WAIVED are reviewed design choices (see docs/verification.md, "Verilator lint"); any
other warning category, or any error other than the summary "Exiting due to N
warning(s)", makes the script exit non-zero.
"""
import collections
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "metrics", "verilator_lint.txt")
SOURCES = ["rtl/anc_core.v", "quartus/wm8731_i2c_init.v", "quartus/i2s_transceiver.v",
           "quartus/anc_de2_115_top.v"]
WAIVED = {
    "WIDTHEXPAND": "sign/zero extension in mixed-width arithmetic; behaviour fixed by the bit-exact regression",
    "WIDTHTRUNC": "parameter-derived constants and saturating adds sized at elaboration; bit-exact regression",
    "BLKSEQ": "blocking temporaries inside clocked blocks of anc_core (computed then registered); intentional style",
    "UNUSEDSIGNAL": "unused board inputs (KEY[3:1], SW[3:2]), dropped LSBs of 16-bit ADC words, y_out, I2S status bits",
    "UNUSEDPARAM": "i2s_transceiver DATA_WIDTH kept for interface compatibility (fixed 16-bit codec words)",
    "SYNCASYNCNET": "core uses a synchronous reset, wrapper flops an async-assert reset; rst_n is synchronised first",
}


def main():
    if not shutil.which("verilator"):
        raise SystemExit("verilator not found")
    ver = subprocess.run(["verilator", "--version"], capture_output=True, text=True).stdout.strip()
    p = subprocess.run(["verilator", "--lint-only", "-Wall", "--top-module", "anc_de2_115_top"] + SOURCES,
                       cwd=ROOT, capture_output=True, text=True)
    msgs = [l for l in p.stderr.splitlines() if l.startswith("%")]
    counts = collections.Counter()
    unwaived = []
    for m in msgs:
        w = re.match(r"%Warning-([A-Z0-9_]+):", m)
        if w:
            counts[w.group(1)] += 1
            if w.group(1) not in WAIVED:
                unwaived.append(m)
        elif m.startswith("%Error") and "Exiting due to" not in m:
            counts["ERROR"] += 1
            unwaived.append(m)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(f"Verilator lint (-Wall) of {', '.join(SOURCES)}\n{ver}\n\n")
        f.write("Category counts:\n")
        for k, v in sorted(counts.items()):
            f.write(f"  {k:14s} {v:3d}  {'WAIVED: ' + WAIVED[k] if k in WAIVED else 'NOT WAIVED'}\n")
        f.write(f"\nUnwaived messages: {len(unwaived)}\n")
        for m in unwaived:
            f.write("  " + m + "\n")
        f.write("\nAll messages:\n")
        for m in msgs:
            f.write("  " + m + "\n")
    print(open(OUT).read().split("\nAll messages:")[0])
    sys.exit(1 if unwaived else 0)


if __name__ == "__main__":
    main()

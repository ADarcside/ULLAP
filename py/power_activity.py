"""Relative dynamic-energy proxy per processed sample (RTL switching activity, Icarus).

Simulates tb/tb_power.v for each algorithm at its board setting (W = 12, L = 32, one sample
every 6144 cycles as at 8.138 kHz), dumps a VCD of anc_core and counts bit toggles of every
net and register except the clock. Toggles per sample is a technology-independent proxy for
dynamic energy per sample; it ignores capacitance, glitches and static power, so it ranks the
architectures but does not give milliwatts. Absolute power needs the Quartus Power Analyzer
with a gate-level VCD (docs/power_flow.md).

Output: results/metrics/power_activity.csv
"""
import csv
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build", "power")
VEC = "vectors/rtl/shift_e2_k3_W12_stationary"     # W = 12 stimulus, x/d columns only
N = 1000
CONFIGS = {  # board settings (FAIR_TUNED_SETTINGS as top-level parameters)
    "lms": dict(ALGO=0, MU_INT=256, K=3, EPS_EXP=2),
    "nlms": dict(ALGO=1, MU_INT=256, K=3, EPS_EXP=0),
    "nlms_shift": dict(ALGO=2, MU_INT=512, K=3, EPS_EXP=2),
}


def count_toggles(vcd_path, skip=("clk",)):
    widths, names, last = {}, {}, {}
    toggles = {}
    scope = []
    with open(vcd_path) as f:
        in_defs = True
        for line in f:
            t = line.split()
            if not t:
                continue
            if in_defs:
                if t[0] == "$scope":
                    scope.append(t[2])
                elif t[0] == "$upscope":
                    scope.pop()
                elif t[0] == "$var":
                    w, ident, name = int(t[2]), t[3], t[4]
                    if name in skip:
                        continue
                    widths[ident] = w
                    names[ident] = ".".join(scope[1:] + [name])
                elif t[0] == "$enddefinitions":
                    in_defs = False
                continue
            c = t[0][0]
            if c in "01xzXZ" and len(t) == 1:
                ident, val = t[0][1:], t[0][0]
            elif c in "bB":
                ident, val = t[1], t[0][1:]
            else:
                continue
            if ident not in widths:
                continue
            val = val.zfill(widths[ident]) if val[0] in "01" else val.rjust(widths[ident], val[0])
            prev = last.get(ident)
            if prev is not None:
                toggles[ident] = toggles.get(ident, 0) + sum(a != b for a, b in zip(prev, val))
            last[ident] = val
    return sum(toggles.values()), {names[i]: n for i, n in toggles.items()}


def main():
    os.makedirs(BUILD, exist_ok=True)
    rows = []
    for algo, p in CONFIGS.items():
        vvp = os.path.join(BUILD, algo + ".vvp")
        vcd = os.path.join(BUILD, algo + ".vcd")
        cmd = ["iverilog", "-g2005", "-o", vvp, "-s", "tb_power"] + \
              [f"-Ptb_power.{k}={v}" for k, v in p.items()] + ["rtl/anc_core.v", "tb/tb_power.v"]
        subprocess.run(cmd, cwd=ROOT, check=True)
        out = subprocess.run(["vvp", "-n", vvp, f"+vec={VEC}", f"+vcd={vcd}", f"+n={N}"],
                             cwd=ROOT, capture_output=True, text=True).stdout
        if "TB_POWER DONE" not in out:
            raise SystemExit(out)
        total, per = count_toggles(vcd)
        top = sorted(per.items(), key=lambda kv: -kv[1])[:5]
        rows.append(dict(algo=algo, samples=N, toggles_total=total, toggles_per_sample=round(total / N, 1),
                         top_signals="; ".join(f"{k}={v / N:.0f}" for k, v in top)))
        os.remove(vcd)
    base = next(r for r in rows if r["algo"] == "nlms")["toggles_per_sample"]
    for r in rows:
        r["relative_to_nlms"] = round(r["toggles_per_sample"] / base, 3)
    out = os.path.join(ROOT, "results", "metrics", "power_activity.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    for r in rows:
        print(f"{r['algo']:11s} toggles/sample={r['toggles_per_sample']:9.1f}  x{r['relative_to_nlms']:.3f} vs NLMS  top: {r['top_signals']}")


if __name__ == "__main__":
    sys.exit(main())

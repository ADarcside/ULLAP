"""Gate-level power flow: golden vectors before, energy per sample after (journal study).

The Quartus Power Analyzer run itself needs Quartus + Questa (bench PC, see docs/power_flow.md).
This script does the two steps around it.

    python py/power_gate_level.py vectors
        writes vectors/power/<algo>.vec: the x/d stimulus of py/power_activity.py with the e
        column recomputed by py/rtl_model.py at each algorithm's board setting, so tb/tb_power.v
        can check the gate-level netlist sample by sample.

    python py/power_gate_level.py report <dir>
        reads <dir>/<algo>_<mode>.pow.rpt (mode = board or max) and <dir>/<algo>_<mode>.log
        (the tb_power summary line), writes results/metrics/power_gate_level.csv with
        static, core dynamic, I/O and total power, and the dynamic energy per sample:
          board : core dynamic power / 8,138.02 Hz          (energy per sample at the board rate)
          max   : core dynamic power * gap / 50 MHz         (back-to-back samples, comparable with
                                                             the power/throughput figures of merit)
"""
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from power_activity import CONFIGS, VEC  # noqa: E402
from rtl_model import run_rtl_model  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, L, FCLK, FS = 12, 32, 50e6, 50e6 / 6144
ALGO_ID = {"lms": 0, "nlms": 1, "nlms_shift": 2}


def s2i(h):
    v = int(h, 16)
    return v - (1 << W) if v >= 1 << (W - 1) else v


def vectors():
    rows = [ln.split() for ln in open(os.path.join(ROOT, VEC + ".vec")) if ln.strip()]
    xi, di = [s2i(r[0]) for r in rows], [s2i(r[1]) for r in rows]
    out = os.path.join(ROOT, "vectors", "power")
    os.makedirs(out, exist_ok=True)
    for algo, p in CONFIGS.items():
        r = run_rtl_model(p["ALGO"], xi, di, W, L, MU_INT=p["MU_INT"], K=p["K"], EPS_EXP=p["EPS_EXP"])
        m = (1 << W) - 1
        with open(os.path.join(out, algo + ".vec"), "w", newline="\n") as f:
            for x, d, y, e in zip(xi, di, r["y"], r["e"]):
                f.write(f"{x & m:03X} {d & m:03X} {y & m:03X} {e & m:03X}\n")
        print(f"vectors/power/{algo}.vec  {len(xi)} samples  {p}")


def mw(text, label):
    """Power in mW from a .pow.rpt summary line such as '; Core Dynamic Thermal Power Dissipation ; 12.34 mW ;'."""
    m = re.search(re.escape(label) + r"\s*;\s*([0-9.]+)\s*(mW|W)", text)
    if not m:
        return None
    return float(m.group(1)) * (1000.0 if m.group(2) == "W" else 1.0)


def report(d):
    rows = []
    for algo in CONFIGS:
        for mode in ("board", "max"):
            rpt = os.path.join(d, f"{algo}_{mode}.pow.rpt")
            if not os.path.exists(rpt):
                print(f"missing {rpt}")
                continue
            text = open(rpt, errors="replace").read()
            log = open(os.path.join(d, f"{algo}_{mode}.log"), errors="replace").read()
            tb = re.search(r"TB_POWER DONE samples=(\d+) gap=(\d+) cycles=(\d+) outputs=(\d+) mismatches=(\d+)", log)
            if not tb:
                raise SystemExit(f"{algo}_{mode}.log: no TB_POWER DONE line")
            n, gap, _, nout, bad = map(int, tb.groups())
            conf = re.search(r"Power Estimation Confidence\s*;\s*([^;]+);", text)
            row = dict(algo=algo, mode=mode, samples=n, gap=gap, outputs=nout, mismatches=bad,
                       total_mw=mw(text, "Total Thermal Power Dissipation"),
                       core_dynamic_mw=mw(text, "Core Dynamic Thermal Power Dissipation"),
                       core_static_mw=mw(text, "Core Static Thermal Power Dissipation"),
                       io_mw=mw(text, "I/O Thermal Power Dissipation"),
                       confidence=conf.group(1).strip() if conf else "")
            pd = row["core_dynamic_mw"]
            rate = FS if mode == "board" else FCLK / gap
            row["sample_rate_hz"] = round(rate, 2)
            row["dyn_energy_nj_per_sample"] = round(pd * 1e-3 / rate * 1e9, 3) if pd is not None else None
            rows.append(row)
            print(row)
    if rows:
        path = os.path.join(ROOT, "results", "metrics", "power_gate_level.csv")
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        print("wrote", path)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "vectors":
        vectors()
    elif len(sys.argv) >= 3 and sys.argv[1] == "report":
        report(sys.argv[2])
    else:
        raise SystemExit(__doc__)

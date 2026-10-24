"""Word-length sweep W = 8..16 at the fair-tuned settings, 20 seeds (journal precision study).

Replaces the earlier sweep (W = 8, 10, 12, 14, 16, 20, 24 only, 3 seeds, NLMS float reference
tuned differently), which could not reproduce the W = 12 choice. Here every algorithm uses its
FAIR_TUNED_SETTINGS at every W, and the degradation is measured against the floating-point run
of the same algorithm with the same mu and eps, so it is a pure quantisation loss.

Outputs
  results/metrics/wordlength_fair_raw.csv      one row per (algo, scenario, W, seed)
  results/metrics/wordlength_fair_summary.csv  per (algo, W): mean NR [95% CI], mean and worst-
                                               scenario degradation, overflow count
  results/plots/fig13_wordlength_fair.{png,pdf}
Selection rule (unchanged from the original study): smallest W whose worst-scenario mean
degradation is <= 3.0 dB for every algorithm with zero overflows.
"""
import argparse
import csv
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from algos import run_float  # noqa: E402
from experiment_config import FAIR_TUNED_SETTINGS  # noqa: E402
from fixedpoint import FxCfg, run_fixed  # noqa: E402
from metrics import evaluate  # noqa: E402
from signals import make_scenario  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
SCENARIOS = ("stationary", "amp_steps", "path_switch", "wav")
ALGOS = ("lms", "nlms", "nlms_shift")
THRESH_DB = 3.0
L = 32


def one(job):
    algo, scen, W, seed = job
    s = FAIR_TUNED_SETTINGS[algo]
    mu, eps_exp = s["mu"], s["eps_exp"]
    sc = make_scenario(scen, 16000, seed, WAV if scen == "wav" else None)
    rf = run_float(algo, sc.x, sc.d, L, mu, eps=2.0 ** -eps_exp)
    mf = evaluate(sc, rf["e"], rf["W"], L)
    r = run_fixed(algo, sc.x, sc.d, L, mu, FxCfg(W=W, eps_exp=eps_exp))
    m = evaluate(sc, r["e"], r["W"], L)
    ovf = sum(v for k, v in r["counts"].items() if not k.startswith("in_"))
    return dict(algo=algo, scenario=scen, W=W, seed=seed, nr_final=m["nr_final"],
                nr_float=mf["nr_final"], deg=mf["nr_final"] - m["nr_final"], ovf=ovf,
                in_clip=r["counts"]["in_x"] + r["counts"]["in_d"])


def summarise(rows, wbits):
    import scipy.stats as st
    out = []
    for algo in ALGOS:
        for W in wbits:
            sub = [r for r in rows if r["algo"] == algo and r["W"] == W]
            per_scen = {sc: [r for r in sub if r["scenario"] == sc] for sc in SCENARIOS}
            # mean over scenarios of the per-seed NR, then CI over seeds
            seeds = sorted({r["seed"] for r in sub})
            per_seed = [np.mean([r["nr_final"] for r in sub if r["seed"] == s]) for s in seeds]
            m, sd = float(np.mean(per_seed)), float(np.std(per_seed, ddof=1))
            ci = float(st.t.ppf(0.975, len(seeds) - 1) * sd / np.sqrt(len(seeds)))
            deg_s = {sc: float(np.mean([r["deg"] for r in v])) for sc, v in per_scen.items()}
            worst = max(deg_s, key=deg_s.get)
            out.append(dict(algo=algo, W=W, nr_mean=round(m, 2), nr_ci95=round(ci, 2),
                            deg_mean=round(float(np.mean(list(deg_s.values()))), 2),
                            deg_worst=round(deg_s[worst], 2), worst_scenario=worst,
                            ovf=int(sum(r["ovf"] for r in sub)),
                            **{f"deg_{sc}": round(v, 2) for sc, v in deg_s.items()}))
    return out


def plot(summary, wbits, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.6))
    style = {"lms": ("#4C72B0", "o"), "nlms": ("#DD8452", "s"), "nlms_shift": ("#55A868", "^")}
    label = {"lms": "LMS", "nlms": "NLMS", "nlms_shift": "NLMS-Shift"}
    for algo in ALGOS:
        rs_ = [r for r in summary if r["algo"] == algo]
        c, mk = style[algo]
        ax[0].errorbar(wbits, [r["nr_mean"] for r in rs_], yerr=[r["nr_ci95"] for r in rs_],
                       color=c, marker=mk, capsize=3, label=label[algo])
        ax[1].plot(wbits, [r["deg_worst"] for r in rs_], color=c, marker=mk, label=label[algo])
    ax[1].axhline(THRESH_DB, color="0.4", ls="--", lw=1)
    ax[1].text(wbits[-1], THRESH_DB + 0.2, "3 dB threshold", ha="right", fontsize=8, color="0.3")
    ax[0].set(xlabel="Word length W (bits)", ylabel="Final NR, mean of 4 scenarios (dB)",
              title="Cancellation vs word length (20 seeds, 95% CI)")
    ax[1].set(xlabel="Word length W (bits)", ylabel="Worst-scenario loss vs float (dB)",
              title="Quantisation loss, worst scenario")
    for a in ax:
        a.grid(alpha=0.3); a.set_xticks(wbits)
    ax[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path + ".png", dpi=300)
    fig.savefig(path + ".pdf")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--wmin", type=int, default=8)
    ap.add_argument("--wmax", type=int, default=16)
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    a = ap.parse_args(argv)
    wbits = list(range(a.wmin, a.wmax + 1))
    jobs = [(al, sc, W, s) for al in ALGOS for sc in SCENARIOS for W in wbits for s in range(1, a.seeds + 1)]
    with ProcessPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(one, jobs, chunksize=8))
    mdir = os.path.join(ROOT, "results", "metrics")
    with open(os.path.join(mdir, "wordlength_fair_raw.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    summary = summarise(rows, wbits)
    with open(os.path.join(mdir, "wordlength_fair_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader(); w.writerows(summary)
    plot(summary, wbits, os.path.join(ROOT, "results", "plots", "fig13_wordlength_fair"))
    ok = [W for W in wbits if all(r["deg_worst"] <= THRESH_DB and r["ovf"] == 0
                                  for r in summary if r["W"] == W)]
    for r in summary:
        print(f"{r['algo']:11s} W={r['W']:2d} NR={r['nr_mean']:6.2f}+-{r['nr_ci95']:.2f} "
              f"deg_mean={r['deg_mean']:5.2f} worst={r['deg_worst']:5.2f} ({r['worst_scenario']}) ovf={r['ovf']}")
    print(f"Smallest W meeting worst-scenario loss <= {THRESH_DB} dB with zero overflow for all algorithms: "
          f"{min(ok) if ok else 'none'}")


if __name__ == "__main__":
    main()

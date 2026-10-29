"""Paired per-seed statistics for the headline comparison (closes docs/claims.md known limit 7).

Re-runs the fair-tuned W = 12 fixed-point models on seeds 1-20 for every scenario, keeps the
per-seed final NR, and for each algorithm pair reports the mean paired difference with a 95% CI,
a paired t-test p-value, a Wilcoxon signed-rank p-value, and a TOST equivalence test with a
+/-0.5 dB margin (equivalent if both one-sided tests give p < 0.05). "Tie" in the paper then
means TOST-equivalent, not merely overlapping CIs.

Outputs: results/metrics/paired_seed_nr.csv (per seed), results/metrics/paired_stats.csv
"""
import csv
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment_config import FAIR_TUNED_SETTINGS  # noqa: E402
from fixedpoint import FxCfg, run_fixed  # noqa: E402
from metrics import evaluate  # noqa: E402
from signals import make_scenario  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
SCENARIOS = ("stationary", "amp_steps", "path_switch", "wav")
ALGOS = ("lms", "nlms", "nlms_shift")
PAIRS = (("nlms_shift", "nlms"), ("nlms_shift", "lms"), ("nlms", "lms"))
MARGIN = 0.5


def one(job):
    algo, scen, seed = job
    s = FAIR_TUNED_SETTINGS[algo]
    sc = make_scenario(scen, 16000, seed, WAV if scen == "wav" else None)
    r = run_fixed(algo, sc.x, sc.d, 32, s["mu"], FxCfg(W=12, eps_exp=s["eps_exp"]))
    return dict(algo=algo, scenario=scen, seed=seed, nr_final=evaluate(sc, r["e"], r["W"], 32)["nr_final"])


def paired(a, b):
    from scipy import stats
    d = np.asarray(a) - np.asarray(b)
    n = len(d)
    m, se = d.mean(), d.std(ddof=1) / np.sqrt(n)
    tcrit = stats.t.ppf(0.975, n - 1)
    p_t = stats.ttest_rel(a, b).pvalue
    p_w = stats.wilcoxon(a, b).pvalue if np.any(d != 0) else 1.0
    p_lo = 1 - stats.t.cdf((m + MARGIN) / se, n - 1)     # H0: diff <= -margin
    p_hi = stats.t.cdf((m - MARGIN) / se, n - 1)         # H0: diff >= +margin
    return dict(mean_diff=round(m, 3), ci95_low=round(m - tcrit * se, 3), ci95_high=round(m + tcrit * se, 3),
                p_ttest=float(f"{p_t:.3g}"), p_wilcoxon=float(f"{p_w:.3g}"),
                p_tost=float(f"{max(p_lo, p_hi):.3g}"), equivalent=bool(max(p_lo, p_hi) < 0.05))


def main():
    jobs = [(al, sc, s) for al in ALGOS for sc in SCENARIOS for s in range(1, 21)]
    with ProcessPoolExecutor(os.cpu_count()) as ex:
        rows = list(ex.map(one, jobs, chunksize=4))
    mdir = os.path.join(ROOT, "results", "metrics")
    with open(os.path.join(mdir, "paired_seed_nr.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    out = []
    for sc in SCENARIOS:
        get = lambda al: [r["nr_final"] for r in sorted(rows, key=lambda r: r["seed"])
                          if r["algo"] == al and r["scenario"] == sc]
        means = {al: round(float(np.mean(get(al))), 2) for al in ALGOS}
        for a, b in PAIRS:
            out.append(dict(scenario=sc, a=a, b=b, mean_a=means[a], mean_b=means[b], **paired(get(a), get(b))))
    with open(os.path.join(mdir, "paired_stats.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    for r in out:
        print(f"{r['scenario']:11s} {r['a']:10s}-{r['b']:10s} {r['mean_a']:6.2f}/{r['mean_b']:6.2f} diff={r['mean_diff']:+.2f} "
              f"[{r['ci95_low']:+.2f},{r['ci95_high']:+.2f}] p_t={r['p_ttest']:.3g} p_w={r['p_wilcoxon']:.3g} "
              f"TOST(+/-{MARGIN})={'EQUIV' if r['equivalent'] else 'no'} (p={r['p_tost']:.3g})")


if __name__ == "__main__":
    main()

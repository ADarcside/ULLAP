"""Equivalent step size of NLMS-Shift (journal study, bit-exact integer model).

NLMS-Shift uses mu[n] = 2^-(floor(log2(P+eps)) + 1 + K), which equals the NLMS step mu/(P+eps)
with mu = 2^-K times the ratio r = (P+eps) / 2^(floor(log2(P+eps)) + 1), r in [0.5, 1).
Averaged over levels spread uniformly on a log scale, E[r] = 1/(2 ln 2) = 0.721. At a fixed
level r is set by where P+eps lies within its octave: it rises with the level and halves when
P+eps crosses a power of two (every 3 dB of input level once P dominates eps). Broadband noise spreads P over the
window and smooths this sawtooth; a tonal reference keeps P almost constant, so r jumps.

Level sweep in 0.75 dB steps around the paper's level, W = 12, L = 32, K = 3, eps = 2^-2:
  broadband : synthetic stationary scenario (py/signals.py), seeds 1-5
  tonal     : two-sine reference (0.031 and 0.113 cycles/sample), 16-tap path, seed 1
NLMS-Shift is compared with NLMS at mu = r * 2^-K (r measured on the same signal) and at
mu = 2^-K = 0.125: final noise reduction (last 4000 samples) and convergence time (first sample
at which the 256-sample residual power is within 3 dB of its final value).

    python py/exp_equiv_step.py              # writes results/metrics/equiv_step.csv and fig16_equiv_step
    python py/exp_equiv_step.py --plot       # figure only, from the CSV
"""
import argparse
import csv
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fixedpoint import FxCfg, run_fixed  # noqa: E402
from signals import make_scenario  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N, L, K, EPS_EXP = 16000, 32, 3, 2
FINAL = slice(12000, None)
LEVELS = np.arange(-6.0, 6.01, 0.75)          # dB relative to the paper's level
CFG = FxCfg(W=12, eps_exp=EPS_EXP)


def tonal(gain):
    n = np.arange(N)
    h = np.random.default_rng(5).standard_normal(16) * np.exp(-np.arange(16) / 4)
    h /= np.linalg.norm(h)
    x = np.sin(2 * np.pi * 0.031 * n) + 0.7 * np.sin(2 * np.pi * 0.113 * n + 1)
    x = gain * 0.06 * x / x.std()
    s = 0.03 * np.sin(2 * np.pi * 0.0077 * n ** 1.02)
    d = s + np.convolve(x, h)[:N] + 1e-3 * np.random.default_rng(1).standard_normal(N)
    return x, d, s


def signals(kind, gain, seed):
    if kind == "tonal":
        return tonal(gain)
    sc = make_scenario("stationary", N, seed)
    return sc.x * gain, (sc.d - sc.s) * gain + sc.s, sc.s


def ratio(x):
    P = np.convolve(x ** 2, np.ones(L))[L:len(x)] + 2.0 ** -EPS_EXP
    return float(np.mean(P / 2.0 ** (np.floor(np.log2(P)) + 1)))


def tconv(res):
    """First sample at which the 256-sample mean residual power is within 3 dB of its final value."""
    sm = np.convolve(res ** 2, np.ones(256) / 256, "valid")
    return int(np.argmax(sm < 2 * sm[-3000:].mean())) + 256


def one(job):
    kind, lvl, seed = job
    x, d, s = signals(kind, 10 ** (lvl / 20), seed)
    nz = d - s
    out = dict(kind=kind, level_db=lvl, seed=seed, x_rms_dbfs=20 * np.log10(x.std()), r=ratio(x))
    for name, algo, mu in (("shift", "nlms_shift", 2.0 ** -K), ("nlms_r", "nlms", out["r"] * 2.0 ** -K),
                           ("nlms_k", "nlms", 2.0 ** -K)):
        e = np.asarray(run_fixed(algo, x, d, L, mu, CFG)["e"], float)
        out["nr_" + name] = 10 * np.log10(np.mean(nz[FINAL] ** 2) / np.mean((e[FINAL] - s[FINAL]) ** 2))
        out["t_" + name] = tconv(e - s)
    return out


def plot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from visualize import ALGO_COLORS
    with open(os.path.join(ROOT, "results", "metrics", "equiv_step.csv")) as f:
        rows = list(csv.DictReader(f))
    fig, ax = plt.subplots(2, 2, figsize=(7.2, 4.6), sharex=True)
    for j, kind in enumerate(("broadband", "tonal")):
        sub = [r for r in rows if r["kind"] == kind]
        lv = [float(r["x_rms_dbfs"]) for r in sub]
        ax[0, j].plot(lv, [float(r["r"]) for r in sub], "k.-")
        ax[0, j].axhline(1 / (2 * np.log(2)), color="0.6", ls=":", lw=1)
        ax[0, j].set_ylim(0.5, 1.0)
        ax[0, j].set_title(f"{kind} reference")
        ax[1, j].plot(lv, [float(r["nr_shift"]) for r in sub], "o-", ms=3, color=ALGO_COLORS["nlms_shift"], label="NLMS-Shift")
        ax[1, j].plot(lv, [float(r["nr_nlms_r"]) for r in sub], "--", color=ALGO_COLORS["nlms"], label=r"NLMS, $\mu=\bar r\,2^{-K}$")
        ax[1, j].plot(lv, [float(r["nr_nlms_k"]) for r in sub], ":", color="0.4", label=r"NLMS, $\mu=2^{-K}$")
        ax[1, j].set_xlabel("reference RMS (dBFS)")
        for a in ax[:, j]:
            a.grid(alpha=0.3)
    ax[0, 0].set_ylabel(r"mean ratio $\bar r$")
    ax[1, 0].set_ylabel("final NR (dB)")
    ax[1, 0].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    out = os.path.join(ROOT, "results", "plots", "fig16_equiv_step")
    for ext in ("pdf", "png"):
        fig.savefig(f"{out}.{ext}", dpi=200)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plot", action="store_true", help="only redraw the figure from the CSV")
    if ap.parse_args().plot:
        return plot()
    jobs = [(k, lv, s) for k in ("broadband", "tonal") for lv in LEVELS for s in ((1, 2, 3, 4, 5) if k == "broadband" else (1,))]
    with ProcessPoolExecutor() as ex:
        rows = list(ex.map(one, jobs))
    keys = ("x_rms_dbfs", "r", "nr_shift", "nr_nlms_r", "nr_nlms_k", "t_shift", "t_nlms_r", "t_nlms_k")
    out = []
    for kind in ("broadband", "tonal"):
        for lv in LEVELS:
            sub = [r for r in rows if r["kind"] == kind and r["level_db"] == lv]
            row = dict(kind=kind, level_db=round(float(lv), 2), n=len(sub))
            row.update({k: round(float(np.mean([r[k] for r in sub])), 3) for k in keys})
            out.append(row)
            print(f"{kind:9s} {row['level_db']:+5.2f} dB  x {row['x_rms_dbfs']:6.1f} dBFS  r {row['r']:.3f}  "
                  f"NR {row['nr_shift']:6.2f} {row['nr_nlms_r']:6.2f} {row['nr_nlms_k']:6.2f}  "
                  f"t {row['t_shift']:6.0f} {row['t_nlms_r']:6.0f} {row['t_nlms_k']:6.0f}  (shift, NLMS r/8, NLMS 1/8)")
    with open(os.path.join(ROOT, "results", "metrics", "equiv_step.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    plot()


if __name__ == "__main__":
    main()

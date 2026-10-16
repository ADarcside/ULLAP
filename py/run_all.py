#!/usr/bin/env python3
"""Full ANC study: tune -> float comparison -> fixed-point sweep -> candidates -> figures/docs/vectors.

  python py/run_all.py [--wav noise.wav] [--quick] [--jobs N]
"""
import argparse
import csv
import glob
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from algos import run_float
from fixedpoint import FxCfg, run_fixed, write_vec
from metrics import evaluate, curves, FS
from signals import make_scenario, SCENARIOS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALGOS = ("lms", "nlms", "nlms_shift")
GRID = {"lms": np.geomspace(0.05, 20, 14), "nlms": np.geomspace(0.01, 1.0, 13),
        "nlms_shift": 2.0 ** -np.arange(0, 9)}
TUNE_SEED, EVAL_SEEDS = 100, (1, 2, 3)
THR = dict(mean_deg=1.0, max_deg=3.0, ovf_rate=1e-3, min_nr=10.0)   # candidate-selection thresholds
STRUCT = {"lms": "2L+1 mult, no divider", "nlms": "2L+3 mult + 1 divider (or reciprocal)",
          "nlms_shift": "2L mult, leading-one detect + barrel shift, no divider/mu-mult"}


# ---------------------------------------------------------------- workers
def job(t):
    kind, algo, name, seed, mu, cfg, wav, n, L = t
    sc = make_scenario(name, n, seed, wav)
    if kind == "float":
        r, cnt = run_float(algo, sc.x, sc.d, L, mu), {}
    else:
        r = run_fixed(algo, sc.x, sc.d, L, mu, cfg)
        cnt = r["counts"]
    m = evaluate(sc, r["e"], r["W"], L)
    m.update(kind=kind, algo=algo, scenario=name, seed=seed, mu=float(mu), Wbits=cfg.W if cfg else 0,
             acc_bits=r.get("acc_bits", 0), ovf=sum(cnt.values()), **cnt)
    return m


def pmap(tasks, jobs):
    if jobs <= 1:
        return [job(t) for t in tasks]
    with Pool(jobs) as p:
        return p.map(job, tasks, chunksize=4)


def save_csv(path, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(rows)


def sel(rows, **kw):
    return [r for r in rows if all(r[k] == v for k, v in kw.items())]


def fmt(v, p=1):
    return "n/a" if v is None or (isinstance(v, float) and np.isnan(v)) else ("inf" if np.isinf(v) else f"{v:.{p}f}")


def table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] +
                     ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


# ---------------------------------------------------------------- plots
def plot_grid(names, data, key, ylabel, fname, events, noise_key=None):
    nr = (len(names) + 1) // 2
    fig, ax = plt.subplots(nr, 2, figsize=(11, 3.3 * nr), squeeze=False)
    for a, nm in zip(ax.ravel(), names):
        t = np.arange(len(data[nm][ALGOS[0]][key])) / FS
        if noise_key:
            a.plot(t[::8], data[nm][ALGOS[0]][noise_key][::8], "k--", lw=.8, label="noise input")
        for al in ALGOS:
            a.plot(t[::8], data[nm][al][key][::8], lw=1, label=al)
        for ev in events[nm]:
            a.axvline(ev / FS, color="gray", ls=":")
        a.set(title=nm, xlabel="time (s)", ylabel=ylabel)
        a.grid(alpha=.3)
    for a in ax.ravel()[len(names):]:
        a.axis("off")
    ax[0, 0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(fname, dpi=110)
    plt.close(fig)


def plot_summary(names, FL, fname, cap_ms):
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))
    x, wd = np.arange(len(names)), 0.27
    for j, (key, title, yl) in enumerate((("nr_final", "Final noise reduction", "dB"),
                                          ("time", "Settling (1st) time, capped", "ms"),
                                          ("coef_db", "Final coefficient error", "dB (lower = better)"))):
        for i, al in enumerate(ALGOS):
            v = [FL[(nm, al)]["settle_ms"] if key == "time" else FL[(nm, al)][key] for nm in names]
            v = [min(u, cap_ms) for u in v] if key == "time" else v
            ax[j].bar(x + (i - 1) * wd, v, wd, label=al)
        ax[j].set(title=title, ylabel=yl, xticks=x, xticklabels=names)
        ax[j].grid(axis="y", alpha=.3)
    ax[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(fname, dpi=110)
    plt.close(fig)


def plot_fixed(widths, S, fname):
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))
    for al in ALGOS:
        ax[0].plot(widths, [S[(al, w)]["nr"] for w in widths], "o-", ms=3, label=al)
        ax[1].plot(widths, [S[(al, w)]["mean_deg"] for w in widths], "o-", ms=3, label=al)
        ax[2].plot(widths, [S[(al, w)]["coef"] for w in widths], "o-", ms=3, label=al)
    ax[0].set(title="Mean final NR (fixed point)", ylabel="dB")
    ax[1].set(title="Mean degradation vs float", ylabel="dB")
    ax[1].axhline(THR["mean_deg"], color="gray", ls=":")
    ax[2].set(title="Mean final coefficient error (fixed point)", ylabel="dB (lower = better)")
    for a in ax:
        a.set(xlabel="total width W (bits)")
        a.grid(alpha=.3)
    ax[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(fname, dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", help="real-audio noise WAV (default: first vectors/*.wav, else scenario skipped)")
    ap.add_argument("--n", type=int, default=16000)
    ap.add_argument("--L", type=int, default=32)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--quick", action="store_true", help="smoke run: fewer widths/seeds/grid points")
    a = ap.parse_args()
    n, L, T0 = a.n, a.L, time.time()
    wav = a.wav or next(iter(sorted(glob.glob(os.path.join(ROOT, "vectors", "*.wav")))), None)
    names = [s for s in SCENARIOS if s != "wav" or wav]
    if not wav:
        print("NOTE: no WAV given/found -> scenario 'wav' skipped")
    seeds = EVAL_SEEDS[:1] if a.quick else EVAL_SEEDS
    widths = [8, 12, 16, 20, 24] if a.quick else list(range(8, 25))
    grid = {k: (v[::2] if a.quick else v) for k, v in GRID.items()}
    D, FIG, VEC = (os.path.join(ROOT, p) for p in ("docs/data", "docs/figures", "vectors"))
    for p in (D, FIG, VEC):
        os.makedirs(p, exist_ok=True)
    log = lambda m: print(f"[{time.time() - T0:6.1f}s] {m}", flush=True)

    # 1. fair step-size tuning: one mu per algorithm, shared by all scenarios, tuned on an unseen seed
    rows = pmap([("float", al, nm, TUNE_SEED, mu, None, wav, n, L)
                 for al in ALGOS for mu in grid[al] for nm in names], a.jobs)
    tune, best = [], {}
    for al in ALGOS:
        for mu in grid[al]:
            sc_ = np.mean([r["nr_avg"] for r in rows if r["algo"] == al and r["mu"] == float(mu)])
            tune.append(dict(algo=al, mu=float(mu), mean_nr_avg=sc_))
        best[al] = max((t for t in tune if t["algo"] == al), key=lambda t: t["mean_nr_avg"])["mu"]
    save_csv(os.path.join(D, "tuning.csv"), tune)
    log(f"tuned mu: {best}")

    # 2. floating-point comparison (3 seeds)
    rows = pmap([("float", al, nm, s, best[al], None, wav, n, L) for al in ALGOS for nm in names for s in seeds], a.jobs)
    save_csv(os.path.join(D, "float_results.csv"), rows)
    FL = {}
    for nm in names:
        for al in ALGOS:
            r = sel(rows, scenario=nm, algo=al)
            g = lambda k: [x[k] for x in r]
            FL[(nm, al)] = dict(nr_final=np.mean(g("nr_final")), nr_std=np.std(g("nr_final")), nr_all=np.mean(g("nr_all")),
                                settle_ms=float(np.median(g("settle_ms"))), track_ms=float(np.median(g("track_ms"))),
                                coef_db=np.mean(g("coef_db")), div=sum(g("diverged")))
    log("float comparison done")

    # 3. plots from seed-1 runs
    cur, ev = {}, {}
    for nm in names:
        sc = make_scenario(nm, n, 1, wav)
        ev[nm] = sc.events
        cur[nm] = {al: curves(sc, (r := run_float(al, sc.x, sc.d, L, best[al]))["e"], r["W"], L) for al in ALGOS}
    plot_grid(names, cur, "nr", "NR (dB, 256-sample)", os.path.join(FIG, "convergence.png"), ev)
    plot_grid(names, cur, "res_db", "residual power (dB)", os.path.join(FIG, "residual.png"), ev, "noise_db")
    plot_grid(names, cur, "coef_db", "||w-h||^2/||h||^2 (dB)", os.path.join(FIG, "coef_error.png"), ev)
    plot_summary(names, FL, os.path.join(FIG, "summary.png"), 1000.0 * n / FS)
    log("float plots done")

    # 4. fixed-point sweep (seed 1, tuned float mu, W = 8..24)
    fx = pmap([("fixed", al, nm, 1, best[al], FxCfg(W=w), wav, n, L) for al in ALGOS for w in widths for nm in names], a.jobs)
    flref = {(r["scenario"], r["algo"]): r["nr_final"] for r in rows if r["seed"] == 1}
    for r in fx:
        r["deg"] = flref[(r["scenario"], r["algo"])] - r["nr_final"]
    save_csv(os.path.join(D, "fixed_sweep.csv"), fx)
    S = {}
    for al in ALGOS:
        for w in widths:
            r = sel(fx, algo=al, Wbits=w)
            S[(al, w)] = dict(nr=np.mean([x["nr_final"] for x in r]), coef=np.mean([x["coef_db"] for x in r]), mean_deg=np.mean([x["deg"] for x in r]),
                              max_deg=max(x["deg"] for x in r), ovf=sum(x["ovf"] for x in r),
                              ovf_rate=sum(x["ovf"] for x in r) / (n * len(names)))
            S[(al, w)]["ok"] = (S[(al, w)]["mean_deg"] <= THR["mean_deg"] and S[(al, w)]["max_deg"] <= THR["max_deg"]
                                and S[(al, w)]["ovf_rate"] <= THR["ovf_rate"] and S[(al, w)]["nr"] >= THR["min_nr"])
    plot_fixed(widths, S, os.path.join(FIG, "fixed_point.png"))
    log("fixed-point sweep done")

    # 5. candidates: per algorithm, smallest W such that W and every larger swept width pass thresholds
    cands = []
    for al in ALGOS:
        ok = [w for w in widths if all(S[(al, v)]["ok"] for v in widths if v >= w)]
        if ok:
            w = ok[0]
            cands.append(dict(algo=al, W=w, mu=best[al], nr_fixed=S[(al, w)]["nr"],
                              nr_float=np.mean([flref[(nm, al)] for nm in names]),
                              mean_deg=S[(al, w)]["mean_deg"],
                              deg_plus1=S[(al, w + 1)]["mean_deg"] if w + 1 in widths else float("nan"), ovf=S[(al, w)]["ovf"], structure=STRUCT[al]))
    cands.sort(key=lambda c: -c["nr_fixed"])
    cands = cands[:3]
    # accumulator-width ablation on candidates (seed 1)
    abl = []
    for c in cands:
        for ab in (2 * c["W"] + (L - 1).bit_length(), 2 * c["W"], 2 * c["W"] - 2, 2 * c["W"] - 4):
            r = pmap([("fixed", c["algo"], nm, 1, c["mu"], FxCfg(W=c["W"], acc_bits=ab), wav, n, L) for nm in names], 1)
            abl.append(dict(algo=c["algo"], W=c["W"], acc_bits=ab, mean_nr=np.mean([x["nr_final"] for x in r]),
                            acc_sat=sum(x["acc"] for x in r), ovf_total=sum(x["ovf"] for x in r)))
    save_csv(os.path.join(D, "acc_ablation.csv"), abl)
    # test vectors for the future RTL testbench (first 4096 samples)
    nv = min(4096, n)
    for c in cands:
        for nm in ("stationary", "path_switch"):
            sc = make_scenario(nm, n, 1, wav)
            write_vec(os.path.join(VEC, f"{c['algo']}_W{c['W']}_{nm}"),
                      run_fixed(c["algo"], sc.x, sc.d, L, c["mu"], FxCfg(W=c["W"])), nv)
    json.dump(dict(mu=best, candidates=cands, thresholds=THR, wav=wav, n=n, L=L, widths=widths),
              open(os.path.join(D, "summary.json"), "w"), indent=1, default=float)

    # 6. docs/results.md (generated)
    o = [f"# Results (generated by py/run_all.py{' --quick' if a.quick else ''}; N={n} samples @ {FS} Hz, L={L})", "",
         f"Scenarios: {', '.join(names)}" + (f"; WAV noise source: `{os.path.basename(wav)}`" if wav else "; no WAV scenario"),
         f"Eval seeds {list(seeds)}; tuning seed {TUNE_SEED} (unseen). Times: median over seeds. NR/coef: mean over seeds.", "",
         "## Tuned step sizes (single mu per algorithm, maximises the mean time-averaged NR (dB) over all scenarios)", "",
         table(["algo", "mu", "grid points"], [[al, f"{best[al]:.4g}", len(grid[al])] for al in ALGOS]), "",
         "## Floating-point comparison", "",
         table(["scenario", "algo", "NR final dB", "NR whole-run dB (power-weighted)", "settle ms", "track ms", "coef err dB", "diverged runs"],
               [[nm, al, f"{FL[(nm, al)]['nr_final']:.1f} ± {FL[(nm, al)]['nr_std']:.1f}", fmt(FL[(nm, al)]["nr_all"]),
                 fmt(FL[(nm, al)]["settle_ms"], 0) + ("*" if FL[(nm, al)]["settle_ms"] > .85 * 1000.0 * (ev[nm][0] if ev[nm] else n) / FS else ""),
                 fmt(FL[(nm, al)]["track_ms"], 0), fmt(FL[(nm, al)]["coef_db"]),
                 FL[(nm, al)]["div"]] for nm in names for al in ALGOS]), "",
         "`*` = settling time > 85 % of the first segment: coefficients still converging when the segment ended (not settled). "
         "Times use the coefficient-error curve; a tracking time of 0 means the event did not disturb the coefficients by > 3 dB.", "",
         "## Fixed-point sweep (seed 1; cells: mean final NR dB / mean degradation dB / overflow events over all scenarios)", "",
         table(["W"] + list(ALGOS), [[w] + [f"{S[(al, w)]['nr']:.1f} / {S[(al, w)]['mean_deg']:+.1f} / {S[(al, w)]['ovf']}"
                                            for al in ALGOS] for w in widths]), "",
         f"Selection thresholds: mean degradation <= {THR['mean_deg']} dB, worst scenario <= {THR['max_deg']} dB, "
         f"overflow rate <= {THR['ovf_rate']}/sample, mean fixed NR >= {THR['min_nr']} dB, for W and all larger swept widths.", "",
         "## Candidate configurations for later FPGA implementation (NOT synthesized: no resource/timing claims)", "",
         "W = smallest swept width meeting the thresholds; NR columns are seed 1 (fixed and float), averaged over scenarios. "
         "The minimum-W point can sit close to a threshold, so the W+1 degradation is shown as a design margin.", "",
         table(["algo", "W (F=W-1)", "mu", "fixed NR dB", "float NR dB", "degr. dB at W", "degr. dB at W+1", "overflows", "arithmetic structure"],
               [[c["algo"], c["W"], f"{c['mu']:.4g}", fmt(c["nr_fixed"]), fmt(c["nr_float"]), f"{c['mean_deg']:+.2f}", f"{c['deg_plus1']:+.2f}", c["ovf"],
                 c["structure"]] for c in cands]) if cands else "No algorithm met the thresholds at any W <= 24.", "",
         "## Accumulator-width ablation (candidates; full width = 2W+ceil(log2 L))", "",
         table(["algo", "W", "acc bits", "mean NR dB", "acc saturations", "all overflows"],
               [[r["algo"], r["W"], r["acc_bits"], fmt(r["mean_nr"]), r["acc_sat"], r["ovf_total"]] for r in abl]) if abl else "", "",
         "Figures: `docs/figures/{convergence,residual,coef_error,summary,fixed_point}.png`; raw tables: `docs/data/*.csv`."]
    open(os.path.join(ROOT, "docs", "results.md"), "w").write("\n".join(o) + "\n")
    log("done -> docs/results.md")


if __name__ == "__main__":
    main()

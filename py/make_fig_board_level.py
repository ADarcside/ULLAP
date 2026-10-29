"""Paper figure of board session 2: running noise reduction of the board against the integer model on the
same 2 s stimulus, at the simulation level and at the level the board received.

    python py/make_fig_board_level.py board/signaltap_session2_20261026.zip
"""
import argparse
import os
import sys
import tempfile
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_board_capture as abc  # noqa: E402
import analyze_board_session2 as s2  # noqa: E402
from board_stimulus import build  # noqa: E402
from make_fig_board import COLOR, ORDER  # noqa: E402
from rtl_model import run_rtl_model  # noqa: E402


def curves(path, algo, scen, win_s=0.125):
    """Running NR of the board capture, the model at simulation level and the model at board level."""
    x, d, e, _ = abc.load_capture(path)
    k, bad = abc.align_and_check(x, d, e, algo)
    if k is None or bad:
        raise SystemExit(f"{path}: not bit-exact ({bad} samples differ)")
    n = int(round(s2.SECONDS * abc.FS))
    s, _ = s2.scenario_start(x[k:], scen)
    db, eb, xb = d[k + s:k + s + n], e[k + s:k + s + n], x[k + s:k + s + n]
    code, p = abc.ALGOS[algo]
    X, D = build(scen, s2.SECONDS, s2.SEED, True)
    X, D = X[:s2.N8K], D[:s2.N8K]
    out = {"board": abc.running_nr(db, eb, int(win_s * abc.FS))}
    for tag, gx, gd in (("sim", 2 ** (abc.W - 1), 2 ** (abc.W - 1)),
                        ("level", np.sqrt(np.mean(xb.astype(float) ** 2) / np.mean(X ** 2)),
                         np.sqrt(np.mean(db.astype(float) ** 2) / np.mean(D ** 2)))):
        xi = np.clip(np.round(X * gx), -2048, 2047).astype(int)
        di = np.clip(np.round(D * gd), -2048, 2047).astype(int)
        em = np.array(run_rtl_model(code, xi.tolist(), di.tolist(), W=abc.W, L=abc.L, **p)["e"])
        t, nr = abc.running_nr(di, em, int(win_s * 8000))
        out[tag] = (t * abc.FS / 8000, nr)      # running_nr assumes the codec rate
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", help="session-2 zip or folder with cap2s_<algo>_<scenario>.csv")
    ap.add_argument("--scenario", default="stationary")
    ap.add_argument("--out", default=os.path.join(abc.ROOT, "results", "plots", "fig15_board_vs_model_stationary"))
    a = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp:
        src = a.src
        if zipfile.is_zipfile(src):
            with zipfile.ZipFile(src) as z:
                z.extractall(tmp, [f"cap2s_{al}_{a.scenario}.csv" for al in ORDER])
            src = tmp
        cur = {al: curves(os.path.join(src, f"cap2s_{al}_{a.scenario}.csv"), al, a.scenario) for al in ORDER}

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.6), sharey=True)
    for ax, al in zip(axs, ORDER):
        c = cur[al]
        ax.plot(*c["sim"], color="#9aa0a6", lw=1.1, label="model, simulation level")
        ax.plot(*c["level"], color=COLOR[al], lw=1.1, ls="--", label="model, board's input level")
        ax.plot(*c["board"], color=COLOR[al], lw=1.1, marker="o", ms=2, label="board capture")
        ax.axvspan(0.75 * s2.SECONDS, s2.SECONDS, color="#fbbc04", alpha=0.15, lw=0)
        ax.set_xlim(0, s2.SECONDS); ax.grid(alpha=0.3); ax.tick_params(labelsize=7)
        ax.set_title(abc.NAMES[al], fontsize=8); ax.set_xlabel("Time in scenario (s)", fontsize=8)
    axs[0].set_ylabel("Noise reduction (dB)", fontsize=8)
    axs[0].legend(loc="lower right", fontsize=6)
    fig.tight_layout()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(f"{a.out}.{ext}", dpi=200)
    print("wrote", a.out + ".{png,pdf}")


if __name__ == "__main__":
    main()

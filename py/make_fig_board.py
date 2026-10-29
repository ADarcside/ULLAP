"""Paper figure of the on-board captures: LMS, NLMS and NLMS-Shift on the same amplitude-step noise.

Reads the session-1 Signal Tap zip, checks each capture bit-exact from the reset, keeps the samples from
the start of the scenario (after the calibration tone, found by correlation with the stimulus) and plots, per algorithm, d and e, then the running noise reduction and the output spectra of all three.

    python py/make_fig_board.py board/signaltap_session1_20261026.zip
"""
import argparse
import os
import sys
import tempfile
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_board_capture as abc  # noqa: E402
from board_stimulus import build  # noqa: E402
from signals import resample_fft  # noqa: E402
from visualize import ALGO_COLORS  # noqa: E402

ORDER = ("lms", "nlms", "shift")
COLOR = {"lms": ALGO_COLORS["lms"], "nlms": ALGO_COLORS["nlms"], "shift": ALGO_COLORS["nlms_shift"]}


def scenario_start(xb, scen, seconds=6.0, tpl_s=2.5):
    """Sample where the session-1 scenario starts in the post-reset capture (KEY0 was pressed by hand
    during the tone, so this differs per capture): correlate x with the first tpl_s of the stimulus."""
    x, _ = build(scen, seconds, 1, True)
    tpl = resample_fft(x[:int(tpl_s * 8000)], int(round(tpl_s * abc.FS)))
    xb = xb.astype(float)
    n, m = len(tpl), len(xb) + len(tpl)
    c = np.fft.irfft(np.fft.rfft(xb, m) * np.conj(np.fft.rfft(tpl, m)), m)[:len(xb) - n + 1]
    rho = np.abs(c) / np.sqrt(np.convolve(xb ** 2, np.ones(n), "valid") * np.sum(tpl ** 2) + 1e-20)
    k = int(np.argmax(rho))
    if rho[k] < 0.5:
        raise SystemExit(f"{scen}: stimulus not found in the capture (correlation {rho[k]:.2f})")
    return k


def load(src, scen):
    """{algo: (d, e)} from the scenario start on (checked bit-exact from the reset), from a capture folder or the session zip."""
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        if zipfile.is_zipfile(src):
            with zipfile.ZipFile(src) as z:
                z.extractall(tmp, [f"cap_{a}_{scen}.csv" for a in ORDER])
            src = tmp
        for a in ORDER:
            x, d, e, _ = abc.load_capture(os.path.join(src, f"cap_{a}_{scen}.csv"))
            k, bad = abc.align_and_check(x, d, e, a)
            if k is None or bad:
                raise SystemExit(f"{a}: capture is not bit-exact ({bad} samples differ)")
            s0 = k + scenario_start(x[k:], scen)
            out[a] = (d[s0:], e[s0:])
    n = min(len(d) for d, _ in out.values())      # same scenario window for all three
    return {a: (d[:n], e[:n]) for a, (d, e) in out.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", help="session-1 zip or folder with cap_<algo>_<scenario>.csv")
    ap.add_argument("--scenario", default="amp_steps")
    ap.add_argument("--out", default=os.path.join(abc.ROOT, "results", "plots", "fig14_board_capture_amp_steps"))
    a = ap.parse_args(argv)
    caps = load(a.src, a.scenario)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fs = 2 ** (abc.W - 1)
    fig = plt.figure(figsize=(7.2, 4.8))
    gs = fig.add_gridspec(2, 3, height_ratios=(1, 1.1))
    for j, al in enumerate(ORDER):
        d, e = caps[al]
        t = np.arange(len(d)) / abc.FS
        ax = fig.add_subplot(gs[0, j], sharey=fig.axes[0] if j else None)
        ax.plot(t, d / fs, lw=0.3, color="#9aa0a6", label="$d$ (before)")
        ax.plot(t, e / fs, lw=0.3, color=COLOR[al], label="$e$ (after)")
        lo = int(0.75 * len(d))
        ax.set_title(f"{abc.NAMES[al]}: NR (last 25 %) = {abc.nr_db(d[lo:], e[lo:]):.1f} dB", fontsize=8)
        ax.set_xlim(0, t[-1]); ax.set_xlabel("Time in scenario (s)", fontsize=8)
        ax.tick_params(labelsize=7)
        if j == 0:
            ax.set_ylabel("Amplitude (FS)", fontsize=8)
        else:
            ax.tick_params(labelleft=False)
        ax.legend(loc="upper left", fontsize=6, handlelength=1)
    ax_nr = fig.add_subplot(gs[1, :2])
    ax_ps = fig.add_subplot(gs[1, 2])
    d0 = caps["shift"][0]
    lo0 = int(0.75 * len(d0))
    f, pd = abc.psd(d0[lo0:])
    ax_ps.plot(f, pd, color="#9aa0a6", lw=1, label="$d$")
    for al in ORDER:
        d, e = caps[al]
        tr, nr = abc.running_nr(d, e, int(0.125 * abc.FS))
        ax_nr.plot(tr, nr, color=COLOR[al], lw=1.1, marker="o", ms=1.8, label=abc.NAMES[al])
        lo = int(0.75 * len(d))
        f, pe = abc.psd(e[lo:])
        ax_ps.plot(f, pe, color=COLOR[al], lw=0.9, label=f"$e$, {abc.NAMES[al]}")
    ax_nr.axvspan(0.75 * len(d0) / abc.FS, len(d0) / abc.FS, color="#fbbc04", alpha=0.15, lw=0)
    ax_nr.set_xlim(0, len(d0) / abc.FS); ax_nr.grid(alpha=0.3)
    ax_nr.set_xlabel("Time in scenario (s)", fontsize=8); ax_nr.set_ylabel("Noise reduction (dB)", fontsize=8)
    ax_nr.legend(loc="lower right", fontsize=7); ax_nr.tick_params(labelsize=7)
    ax_ps.set_xlim(0, abc.FS / 2); ax_ps.grid(alpha=0.3); ax_ps.tick_params(labelsize=7)
    ax_ps.set_xlabel("Frequency (Hz)", fontsize=8); ax_ps.set_ylabel("Power, final 25 % (dB)", fontsize=8)
    ax_ps.legend(loc="upper right", fontsize=5.5, handlelength=1)
    fig.tight_layout()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(f"{a.out}.{ext}", dpi=200)
    print("wrote", a.out + ".{png,pdf}")


if __name__ == "__main__":
    main()

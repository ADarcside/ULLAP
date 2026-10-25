"""Board session 2: 2 s stimulus captures, freeze capture, DAC-word check and soak timing.

Files (CSV exported by Signal Tap, see docs/board_test.md section 4):
    <dir>/cap2s_<lms|nlms|shift>_<scenario>.csv  2 s seed-1 noise-only stimulus (the paper's
                                                16,000-sample simulation signal), played once
    <dir>/cap2s_shift_freeze.csv                stationary, SW[1] (freeze) switched on mid-run
    <dir>/dac_anc.csv, dac_bypass.csv           optional `dac` instance: DAC word vs e / input
    <dir>/timing_soak.csv                       GPIO timing at the end of the 10-minute soak

For the 2 s captures the scenario start is found by correlating the captured reference x with the
stimulus (resampled to the codec rate), so NR_final uses exactly the last 25 % of the 2 s scenario,
the window of the simulations. The same NR is computed for the integer model run on the 8 kHz
stimulus (the digital reference), so the board and simulation are compared on the same signal.

    python py/analyze_board_session2.py board_evidence/signaltap2 --out results/board/session2
"""
import argparse
import csv
import glob
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_board_capture as abc  # noqa: E402
from board_stimulus import build  # noqa: E402
from rtl_model import run_rtl_model  # noqa: E402
from signals import resample_fft  # noqa: E402

SEED, SECONDS = 1, 2.0
N8K = int(SECONDS * 8000)


def q(v):
    return np.clip(np.round(v * 2 ** (abc.W - 1)), -2 ** (abc.W - 1), 2 ** (abc.W - 1) - 1).astype(int)


def digital_reference(algo, scen):
    """NR_final of the integer model on the 8 kHz stimulus (last 25 % of the 2 s scenario)."""
    code, p = abc.ALGOS[algo]
    x, d = build(scen, SECONDS, SEED, True)
    xi, di = q(x[:N8K]), q(d[:N8K])
    e = np.array(run_rtl_model(code, xi.tolist(), di.tolist(), W=abc.W, L=abc.L, **p)["e"])
    lo = int(0.75 * N8K)
    return abc.nr_db(di[lo:], e[lo:]), di, e


def scenario_start(x_board, scen):
    """Index in the post-reset capture where the 2 s scenario starts, and the correlation peak."""
    x, _ = build(scen, SECONDS, SEED, True)
    n = int(round(SECONDS * abc.FS))
    tpl = resample_fft(x[:N8K], n)
    xb = x_board.astype(float)
    if len(xb) < n:
        return None, 0.0
    m = len(xb) + n
    c = np.fft.irfft(np.fft.rfft(xb, m) * np.conj(np.fft.rfft(tpl, m)), m)[:len(xb) - n + 1]
    # normalise by the energy of each capture window so the peak is a correlation coefficient
    e2 = np.convolve(xb ** 2, np.ones(n), "valid")
    rho = np.abs(c) / np.sqrt(e2 * np.sum(tpl ** 2) + 1e-20)
    k = int(np.argmax(rho))
    return k, float(rho[k])


def freeze_check(x, d, e, k0):
    """Find the sample where freeze switched on: the model without freeze reproduces e up to it, the
    model with freeze from that sample reproduces the rest. Returns (switch index or None, mismatches)."""
    code, p = abc.ALGOS["shift"]
    xs, ds, es = x[k0:].tolist(), d[k0:].tolist(), e[k0:]
    free = np.array(run_rtl_model(code, xs, ds, W=abc.W, L=abc.L, **p)["e"])
    bad = np.flatnonzero(free != es)
    if len(bad) == 0:
        return None, 0
    j = int(bad[0])
    best = (None, len(es))
    for f in range(max(0, j - 64), j + 1):
        frz = [0] * f + [1] * (len(xs) - f)
        m = np.array(run_rtl_model(code, xs, ds, W=abc.W, L=abc.L, freeze=frz, **p)["e"])
        nb = int(np.count_nonzero(m != es))
        if nb < best[1]:
            best = (f, nb)
        if nb == 0:
            break
    return best


def dac_check(path, bypass):
    """ANC: the DAC word latched after out_valid equals {e, 4'b0}. Bypass: its top 12 bits equal d."""
    rows = abc.read_rows(path)
    hi, h = abc.find_header(rows, ["e_out", "d_reg"])
    idac = abc.col(h, "dac_left_data[15..0]")
    if idac is None:
        idac = abc.col(h, "adc_right_raw[15..0]") if bypass else abc.col(h, "anc_out_latched[15..0]")
    iv, ie, idd = abc.col(h, "out_valid"), abc.col(h, "e_out"), abc.col(h, "d_reg")
    if idac is None or iv is None:
        return "DAC column not found", 0, 0
    body = [r for r in rows[hi + 1:] if len(r) > max(idac, iv, ie, idd)
            and not any(abc.unknown(r[c]) for c in (idac, iv, ie, idd))]
    rad = abc.detect_radix([r[c] for r in body[:2000] for c in (ie, idd)])
    rad16 = abc.detect_radix([r[idac] for r in body[:2000]])
    ok = bad = 0
    for i in range(len(body) - 1):
        if abc.to_int(body[i][iv], "hex", 1) == 0:     # 1-bit field reads as -1 when set
            continue
        if bypass:
            word = abc.to_int(body[i][idac], rad16, 16)
            ref = abc.to_int(body[i][idd], rad, abc.W)
        else:
            word = abc.to_int(body[i + 1][idac], rad16, 16)     # latched one clock after out_valid
            ref = abc.to_int(body[i][ie], rad, abc.W)
        if (word >> 4) == ref and (bypass or word & 0xF == 0):
            ok += 1
        else:
            bad += 1
    return ("PASS" if ok and not bad else "FAIL"), ok, bad


def plot_2s(tag, d, e, start, n, ref_d, ref_e, nr_b, nr_r, path_base):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    win_b, win_r = int(0.125 * abc.FS), int(0.125 * 8000)
    tb, nb = abc.running_nr(d[start:start + n], e[start:start + n], win_b)
    tr, nr = abc.running_nr(ref_d, ref_e, win_r)
    tr = tr * abc.FS / 8000          # running_nr assumes the codec rate; rescale the 8 kHz time axis
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    ax.plot(tr, nr, color="#9aa0a6", lw=1.2, label=f"integer model, 8 kHz stimulus ({nr_r:.1f} dB)")
    ax.plot(tb, nb, color="#1a73e8", lw=1.2, marker="o", ms=2, label=f"board capture ({nr_b:.1f} dB)")
    ax.axvspan(0.75 * SECONDS, SECONDS, color="#fbbc04", alpha=0.15, lw=0)
    ax.set_xlim(0, SECONDS); ax.set_xlabel("Time in scenario (s)"); ax.set_ylabel("Noise reduction (dB)")
    ax.set_title(tag, fontsize=9); ax.grid(alpha=0.3); ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{path_base}.{ext}", dpi=200)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dir")
    ap.add_argument("--out", default=os.path.join(abc.ROOT, "results", "board", "session2"))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    rows, lines, ok = [], [], True
    n = int(round(SECONDS * abc.FS))
    for path in sorted(glob.glob(os.path.join(a.dir, "cap2s_*.csv"))):
        m = re.match(r"cap2s_(lms|nlms|shift)_(.+)\.csv$", os.path.basename(path))
        if not m:
            continue
        algo, scen = m.groups()
        x, d, e, _ = abc.load_capture(path)
        if scen == "freeze":
            k0, _ = abc.align_and_check(x, d, e, algo)  # the reset; the check fails after the switch
            k0 = k0 if k0 is not None else 0
            f, nb = freeze_check(x, d, e, k0)
            verdict = (f"bit-exact with freeze on from sample {f} ({f / abc.FS:.2f} s after reset)"
                       if f is not None and nb == 0 else f"FAIL ({nb} samples differ)")
            ok &= f is not None and nb == 0
            if f is not None:
                win = int(0.25 * abc.FS)
                pre = abc.nr_db(d[k0 + f - win:k0 + f], e[k0 + f - win:k0 + f])
                end = int(np.flatnonzero(x)[-1]) + 1      # last active sample (silence follows)
                post = abc.nr_db(d[end - win:end], e[end - win:end])
                verdict += f"; NR {pre:.1f} dB in the 0.25 s before the switch, {post:.1f} dB in the last 0.25 s of signal"
            lines.append(f"- Freeze (NLMS-Shift, stationary): {verdict}")
            print("freeze:", verdict)
            continue
        k, bad = abc.align_and_check(x, d, e, algo)
        t9 = "bit-exact" if k is not None and bad == 0 else f"FAIL ({bad})"
        ok &= t9 == "bit-exact"
        k = k or 0
        xb, db, eb = x[k:], d[k:], e[k:]
        s, rho = scenario_start(xb, scen)
        nr_r, ref_d, ref_e = digital_reference(algo, scen)
        if s is None or s + n > len(db) or rho < 0.5:
            nr_b, note = float("nan"), f"scenario not fully inside the capture (start {s}, rho {rho:.2f})"
            ok = False
        else:
            lo = s + int(0.75 * n)
            nr_b, note = abc.nr_db(db[lo:s + n], eb[lo:s + n]), ""
            plot_2s(f"{abc.NAMES[algo]}, {scen}", db, eb, s, n, ref_d, ref_e, nr_b, nr_r,
                    os.path.join(a.out, f"board2s_{algo}_{scen}"))
        rows.append(dict(algorithm=abc.NAMES[algo], scenario=scen, t9=t9, scenario_start_s=round(s / abc.FS, 3) if s is not None else "",
                         corr=round(rho, 3), nr_board_db=round(nr_b, 2), nr_model_db=round(nr_r, 2),
                         diff_db=round(nr_b - nr_r, 2), note=note))
        print(rows[-1])
    for name, byp in (("dac_anc.csv", False), ("dac_bypass.csv", True)):
        p = os.path.join(a.dir, name)
        if os.path.exists(p):
            v, good, badn = dac_check(p, byp)
            ok &= v == "PASS"
            lines.append(f"- DAC word, {'bypass (SW[0] = 1): top 12 bits = d' if byp else 'ANC (SW[0] = 0): = {e, 0000}'}: "
                         f"{v}, {good} samples match, {badn} differ")
            print(lines[-1])
    p = os.path.join(a.dir, "timing_soak.csv")
    if os.path.exists(p):
        res = abc.analyse_timing(p)
        lines.append("- GPIO timing at the end of the 10-minute soak: "
                     + ", ".join(f"{k} {v}" for k, v in res.items()))
        print(lines[-1])
    if rows:
        with open(os.path.join(a.out, "board_session2_summary.csv"), "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0]))
            wr.writeheader(); wr.writerows(rows)
    with open(os.path.join(a.out, "board_session2_summary.md"), "w") as f:
        f.write("# Board session 2\n\n")
        if rows:
            f.write("| Algorithm | Scenario | T9 | NR board (dB) | NR model, same signal (dB) | Difference |\n|---|---|---|---|---|---|\n")
            for r in rows:
                f.write(f"| {r['algorithm']} | {r['scenario']} | {r['t9']} | {r['nr_board_db']} | {r['nr_model_db']} | {r['diff_db']} |\n")
        f.write("\n" + "\n".join(lines) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

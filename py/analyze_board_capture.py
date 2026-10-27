"""Analyse on-board Signal Tap captures: bit-exact check, measured noise reduction, figures.

This replaces audio recording of LINE OUT (board tests T9, T11, and T7/T10 without a scope).
The FPGA itself records, at the codec sample rate, the ADC samples entering the core
(x_reg = reference, d_reg = primary) and the core output e_out, so the noise reduction is
measured on real codec data in the digital domain, and every captured e[n] can be checked
against the integer model.

Capture files (CSV exported from the Signal Tap window, see docs/board_test.md section 4):
    <dir>/cap_<algo>_<scenario>.csv     algo = lms | nlms | shift
    <dir>/timing_<algo>.csv             optional, GPIO[3:0] at 50 MHz (T7, T10)

For each capture:
  * reset alignment: after KEY[0] the core starts from zero weights, so its first output is
    e = d. Rows before the reset (Signal Tap pre-trigger data) are skipped by finding the first
    row from which the integer model, started from zero state, reproduces e[n].
  * T9: PASS when every captured e[n] after the reset equals the model output.
  * NR_final = 10 log10(sum d^2 / sum e^2) over the final 25 % of the post-reset samples (the
    nr_final window of py/metrics.py; the stimulus is noise-only, so d is pure noise).
  * figure: d and e waveforms, running NR (0.25 s windows), and power spectra before/after.

    python py/analyze_board_capture.py board_evidence/signaltap

Writes results/board/board_capture_summary.csv and .md, and results/board/*.png / *.pdf.
"""
import argparse
import csv
import glob
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rtl_model import run_rtl_model  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "board")
FS = 50e6 / 6144                  # codec frame rate with R8 = 0x00C: 8138.02 Hz
CLK = 50e6
W, L = 12, 32
# fair-tuned build parameters (docs/board_test.md section 1)
ALGOS = {"lms": (0, dict(MU_INT=256, K=3, EPS_EXP=2)),
         "nlms": (1, dict(MU_INT=256, K=3, EPS_EXP=0)),
         "shift": (2, dict(MU_INT=512, K=3, EPS_EXP=2))}
NAMES = {"lms": "LMS", "nlms": "NLMS", "shift": "NLMS-Shift"}


# ---------------------------------------------------------------------------- CSV parsing
def read_rows(path):
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        text = f.read()
    delim = max([",", "\t", ";"], key=lambda c: text.count(c))
    return list(csv.reader(text.splitlines(), delimiter=delim))


def find_header(rows, keys):
    for i, row in enumerate(rows):
        low = [c.strip().lower() for c in row]
        # skip the "Groups:" section, whose lines name the buses ("GPIO[3..0] =, GPIO[3], ...")
        if all(any(k in c for c in low) for k in keys) and not any(c.endswith("=") for c in low):
            return i, low
    raise ValueError("no header row containing " + ", ".join(keys))


def col(header, key):
    hits = [i for i, h in enumerate(header) if key in h]
    return hits[0] if hits else None


def detect_radix(tokens):
    toks = [t.strip().strip('"') for t in tokens if t.strip()]
    if any(re.search(r"[a-fA-F]", t.replace("0x", "")) for t in toks):
        return "hex"
    if any(t.startswith("-") for t in toks):
        return "dec"
    return "hex"  # Signal Tap's default bus format


def unknown(tok):
    """Signal Tap writes 'X' (or 'XXX' for a bus) in the first row, before the buffer start."""
    return re.fullmatch(r"X+", tok.strip().strip('"').upper()) is not None


def to_int(tok, radix, bits):
    t = tok.strip().strip('"')
    if t.lower().startswith("0x"):
        t, radix = t[2:], "hex"
    v = int(t, 16) if radix == "hex" else int(t, 10)
    if radix == "hex" or v >= 0:
        v &= (1 << bits) - 1
        if v >> (bits - 1):
            v -= 1 << bits
    return v


def load_capture(path):
    rows = read_rows(path)
    hi, header = find_header(rows, ["x_reg", "d_reg", "e_out"])
    ix, idd, ie = col(header, "x_reg"), col(header, "d_reg"), col(header, "e_out")
    iv = col(header, "out_valid")
    body = [r for r in rows[hi + 1:] if len(r) > max(ix, idd, ie) and r[ix].strip()
            and not any(unknown(r[c]) for c in (ix, idd, ie) + ((iv,) if iv is not None else ()))]
    radix = detect_radix([r[c] for r in body[:4000] for c in (ix, idd, ie)])
    x, d, e = [], [], []
    for r in body:
        if iv is not None and to_int(r[iv], "hex", 1) == 0:
            continue
        x.append(to_int(r[ix], radix, W)); d.append(to_int(r[idd], radix, W)); e.append(to_int(r[ie], radix, W))
    return np.array(x), np.array(d), np.array(e), radix


# ---------------------------------------------------------------------------- analysis
def align_and_check(x, d, e, algo):
    """First row k from which the model started at zero state reproduces e; returns (k, mismatches).

    Starts are only taken where the reference input is active (in silence any start matches), and a
    start that later diverges is dropped and the search resumes after the divergence; the first
    such start is reported if none matches to the end."""
    code, p = ALGOS[algo]
    best = (None, None)
    k = 0
    while k < len(e) - 300:
        # a start inside silence (x = 0) matches the zero-state model by accident: skip it
        if e[k] != d[k] or np.count_nonzero(x[k:k + 300]) < 150 or run_rtl_model(code, x[k:k + 300].tolist(), d[k:k + 300].tolist(),
                                          W=W, L=L, **p)["e"] != list(e[k:k + 300]):
            k += 1
            continue
        full = np.array(run_rtl_model(code, x[k:].tolist(), d[k:].tolist(), W=W, L=L, **p)["e"])
        bad = np.flatnonzero(full != e[k:])
        if len(bad) == 0:
            return k, 0
        if best[0] is None:
            best = (k, len(bad))
        k += int(bad[0]) + 1
    return best


def nr_db(d, e):
    pd, pe = np.mean(d.astype(float) ** 2), np.mean(e.astype(float) ** 2)
    return 10 * np.log10(pd / pe) if pe > 0 else float("inf")


def running_nr(d, e, win):
    n = len(d) // win
    t = (np.arange(n) + 0.5) * win / FS
    return t, np.array([nr_db(d[i * win:(i + 1) * win], e[i * win:(i + 1) * win]) for i in range(n)])


def psd(v, nfft=1024):
    v = v.astype(float) / 2 ** (W - 1)
    seg = [v[i:i + nfft] * np.hanning(nfft) for i in range(0, len(v) - nfft + 1, nfft // 2)]
    p = np.mean([np.abs(np.fft.rfft(s)) ** 2 for s in seg], 0)
    return np.fft.rfftfreq(nfft, 1 / FS), 10 * np.log10(p + 1e-20)


def plot_capture(tag, d, e, nr_final, bitexact, path_base):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = np.arange(len(d)) / FS
    fig, ax = plt.subplots(3, 1, figsize=(7.2, 7.0))
    ax[0].plot(t, d / 2 ** (W - 1), lw=0.4, color="#9aa0a6", label="primary input d (before ANC)")
    ax[0].plot(t, e / 2 ** (W - 1), lw=0.4, color="#1a73e8", label="output e (after ANC)")
    ax[0].set_xlabel("Time after reset (s)"); ax[0].set_ylabel("Amplitude (FS)")
    ax[0].legend(loc="upper right", fontsize=8); ax[0].set_xlim(0, t[-1])
    tr, nr = running_nr(d, e, int(0.25 * FS))
    ax[1].plot(tr, nr, color="#1a73e8", marker="o", ms=2.5, lw=1)
    lo = 0.75 * len(d) / FS
    ax[1].axvspan(lo, t[-1], color="#fbbc04", alpha=0.2, label=f"final 25 %: NR = {nr_final:.2f} dB")
    ax[1].set_xlabel("Time after reset (s)"); ax[1].set_ylabel("Noise reduction (dB)")
    ax[1].legend(loc="lower right", fontsize=8); ax[1].set_xlim(0, t[-1]); ax[1].grid(alpha=0.3)
    seg = slice(int(0.75 * len(d)), len(d))
    f, pd = psd(d[seg]); _, pe = psd(e[seg])
    ax[2].plot(f, pd, color="#9aa0a6", label="d (before)"); ax[2].plot(f, pe, color="#1a73e8", label="e (after)")
    ax[2].set_xlabel("Frequency (Hz)"); ax[2].set_ylabel("Power (dB)"); ax[2].set_xlim(0, FS / 2)
    ax[2].legend(loc="upper right", fontsize=8); ax[2].grid(alpha=0.3)
    fig.suptitle(f"On-board capture, {tag} ({bitexact})", fontsize=10)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{path_base}.{ext}", dpi=200)
    plt.close(fig)


def analyse_timing(path):
    """GPIO[3:0] = {sample_strobe, busy, out_valid, in_valid} sampled at 50 MHz."""
    rows = read_rows(path)
    hi, header = find_header(rows, ["gpio"])
    bits = {int(m.group(1)): i for i, h in enumerate(header)
            for m in [re.search(r"gpio\[(\d)\]$", h)] if m}  # bus exported as separate bits
    body = [r for r in rows[hi + 1:] if len(r) > max(bits.values(), default=col(header, "gpio"))
            and not any(unknown(c) for c in r[1:])]
    if len(bits) == 4:
        g = np.array([sum(to_int(r[i], "dec", 2) << b for b, i in bits.items()) for r in body])
    else:
        ig = col(header, "gpio")
        body = [r for r in body if r[ig].strip()]
        radix = detect_radix([r[ig] for r in body[:2000]])
        g = np.array([to_int(r[ig], radix, 5) & 0xF for r in body])
    bit = lambda b: (g >> b) & 1
    rise = lambda s: np.flatnonzero((s[1:] == 1) & (s[:-1] == 0)) + 1
    iv, ov, busy = bit(0), bit(1), bit(2)
    r_in, r_out = rise(iv), rise(ov)
    res = {}
    if len(r_in) >= 2:
        res["in_valid period (cycles)"] = int(np.median(np.diff(r_in)))
        res["sample rate (Hz)"] = round(CLK / res["in_valid period (cycles)"], 2)
    if len(r_in) and len(r_out):
        lat = [int(o - i) for i in r_in for o in r_out[r_out > i][:1]]
        if lat:
            res["in_valid to out_valid (cycles)"] = int(np.median(lat))
    b_r = rise(busy)
    b_f = np.flatnonzero((busy[1:] == 0) & (busy[:-1] == 1)) + 1
    widths = [int(f - r) for r in b_r for f in b_f[b_f > r][:1]]
    if widths:
        res["busy high (cycles)"] = int(np.median(widths))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dir", help="folder with cap_<algo>_<scenario>.csv files")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    summary, ok = [], True
    for path in sorted(glob.glob(os.path.join(a.dir, "cap_*.csv"))):
        m = re.match(r"cap_(lms|nlms|shift)_(.+)\.csv$", os.path.basename(path))
        if not m:
            print("skip (name not cap_<lms|nlms|shift>_<scenario>.csv):", path)
            continue
        algo, scen = m.groups()
        x, d, e, radix = load_capture(path)
        k, bad = align_and_check(x, d, e, algo)
        if k is None:
            verdict, ok = "no reset found in capture", False
            k = 0
        elif bad:
            verdict, ok = f"FAIL, {bad} samples differ", False
        else:
            verdict = "bit-exact"
        dd, ee = d[k:], e[k:]
        lo = int(0.75 * len(dd))
        nrf = nr_db(dd[lo:], ee[lo:])
        tag = f"{NAMES[algo]}, {scen}"
        plot_capture(tag, dd, ee, nrf, verdict, os.path.join(a.out, f"board_{algo}_{scen}"))
        summary.append(dict(algorithm=NAMES[algo], scenario=scen, samples_after_reset=len(dd),
                            seconds=round(len(dd) / FS, 2), skipped_pre_reset_rows=k, radix=radix,
                            t9_bit_exact=verdict, nr_final_db=round(nrf, 2),
                            d_rms_dbfs=round(10 * np.log10(np.mean((dd / 2 ** 11) ** 2) + 1e-20), 1)))
        print(f"{tag:28s} {len(dd):6d} samples ({len(dd)/FS:.2f} s)  T9: {verdict:22s} NR_final = {nrf:6.2f} dB")
    timing = []
    for path in sorted(glob.glob(os.path.join(a.dir, "timing_*.csv"))):
        res = analyse_timing(path)
        timing.append((os.path.basename(path), res))
        print(os.path.basename(path), res)
    if not summary and not timing:
        raise SystemExit(f"no cap_*.csv or timing_*.csv files in {a.dir}")
    if summary:
        with open(os.path.join(a.out, "board_capture_summary.csv"), "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(summary[0]))
            wr.writeheader(); wr.writerows(summary)
    with open(os.path.join(a.out, "board_capture_summary.md"), "w") as f:
        f.write("# On-board Signal Tap captures\n\n")
        if summary:
            f.write("| Algorithm | Scenario | Samples after reset | Seconds | T9 | NR_final (dB) |\n|---|---|---|---|---|---|\n")
            for s in summary:
                f.write(f"| {s['algorithm']} | {s['scenario']} | {s['samples_after_reset']} | {s['seconds']} | "
                        f"{s['t9_bit_exact']} | {s['nr_final_db']} |\n")
        for name, res in timing:
            f.write(f"\n## {name}\n\n" + "".join(f"- {k}: {v}\n" for k, v in res.items()))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

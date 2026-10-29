"""Board test stimulus and recording analysis (board tests T7 and T11).

make:     writes stereo 16-bit WAVs for LINE IN (left = reference x[n], right = primary d[n])
          for each scenario, at 8 kHz (the board rate) and 48 kHz (for PC playback). Each file
          starts with 1 s of silence and a 0.5 s 1 kHz tone on both channels for level
          calibration and alignment, then the scenario signal repeated to the requested length.
          A noise-only variant (no wanted signal) is written too, which is what T7/T11 use so
          the measured power ratio is a pure noise reduction.
analyze:  given two LINE OUT recordings of the same noise-only stimulus, one with SW[0] = 1
          (bypass, output = d[n]) and one with SW[0] = 0 (ANC, output = e[n]), aligns each to
          the calibration tone and reports NR = 10 log10(P_bypass / P_anc) over the final 25 %
          of the scenario, the same window as nr_final in py/metrics.py.

    python py/board_stimulus.py make --out board/stimulus --seconds 30
    python py/board_stimulus.py analyze --bypass bypass.wav --anc anc.wav --seconds 30
"""
import argparse
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signals import FS, make_scenario, resample_fft  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEAD_S, TONE_S, TONE_HZ, TONE_AMP = 1.0, 0.5, 1000.0, 0.25
SCENARIOS = ("stationary", "amp_steps", "path_switch", "wav")


def write_wav(path, left, right, fs):
    st = np.stack([left, right], 1)
    pcm = np.clip(np.round(st * 32767), -32768, 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(fs)
        w.writeframes(pcm.tobytes())


def read_wav(path):
    with wave.open(path, "rb") as w:
        ch, sw, fs, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise ValueError(f"{path}: only 16-bit PCM supported")
    a = np.frombuffer(raw, "<i2").astype(float).reshape(-1, ch) / 32768.0
    return a, fs


def header(fs):
    lead = np.zeros(int(LEAD_S * fs))
    t = np.arange(int(TONE_S * fs)) / fs
    return np.concatenate([lead, TONE_AMP * np.sin(2 * np.pi * TONE_HZ * t)])


def build(name, seconds, seed, noise_only):
    n = int(seconds * FS)
    wav = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav") if name == "wav" else None
    sc = make_scenario(name, n=n, seed=seed, wav=wav)
    d = sc.d - sc.s if noise_only else sc.d
    return sc.x, d


def cmd_make(a):
    os.makedirs(a.out, exist_ok=True)
    for name in SCENARIOS:
        for noise_only in (True, False):
            x, d = build(name, a.seconds, a.seed, noise_only)
            tag = "noise" if noise_only else "speech"
            for fs in (FS, 48000):
                h = header(fs)
                xs = x if fs == FS else resample_fft(x, round(len(x) * fs / FS))
                ds = d if fs == FS else resample_fft(d, round(len(d) * fs / FS))
                path = os.path.join(a.out, f"{name}_{tag}_{fs // 1000}k.wav")
                write_wav(path, np.concatenate([h, xs]), np.concatenate([h, ds]), fs)
                print("wrote", path)
    return 0


def align(rec, fs):
    """Index of the first sample after the calibration tone (tone found by envelope threshold)."""
    mono = rec.mean(1)
    win = max(1, int(0.01 * fs))
    env = np.sqrt(np.convolve(mono ** 2, np.ones(win) / win, "same"))
    thr = 0.5 * env.max() if env.max() > 0 else 0
    on = np.flatnonzero(env > thr)
    if len(on) == 0:
        raise ValueError("calibration tone not found")
    return on[0] + int(TONE_S * fs)


def nr_final(bypass, anc, fs, seconds):
    sb, sa = align(bypass, fs), align(anc, fs)
    n = int(seconds * fs)
    b = bypass[sb:sb + n].mean(1)
    e = anc[sa:sa + n].mean(1)
    m = min(len(b), len(e))
    lo = int(0.75 * m)
    pb, pa = np.mean(b[lo:m] ** 2), np.mean(e[lo:m] ** 2)
    return 10 * np.log10(pb / pa), pb, pa


def cmd_analyze(a):
    b, fb = read_wav(a.bypass)
    e, fa = read_wav(a.anc)
    if fb != fa:
        raise SystemExit("bypass and ANC recordings have different sample rates")
    nr, pb, pa = nr_final(b, e, fb, a.seconds)
    print(f"T11 NR_final = {nr:.2f} dB (bypass power {10*np.log10(pb):.1f} dBFS, ANC power {10*np.log10(pa):.1f} dBFS)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make"); m.add_argument("--out", default="board/stimulus")
    m.add_argument("--seconds", type=float, default=30.0); m.add_argument("--seed", type=int, default=1)
    z = sub.add_parser("analyze"); z.add_argument("--bypass", required=True); z.add_argument("--anc", required=True)
    z.add_argument("--seconds", type=float, default=30.0)
    a = ap.parse_args(argv)
    return cmd_make(a) if a.cmd == "make" else cmd_analyze(a)


if __name__ == "__main__":
    sys.exit(main())

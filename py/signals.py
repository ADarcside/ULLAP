"""Test-scenario generation for the adaptive noise canceller (ANC) study.

Model:  x = v (noise reference),  d = s + (h * v) + sensor noise,  s = wanted signal.
All signals are float in [-1, 1) so they map directly onto signed Q1.(W-1) fixed point.
"""
import wave
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

FS = 8000
L_TRUE = 16                      # length of the true noise path h
BASE_RMS = 0.06                  # reference-noise RMS at gain 1
SENSOR_STD = 5e-4                # primary-sensor white noise (sets the achievable floor)
COLOR = np.array([1.0, 0.8, 0.6, 0.4, 0.2])   # FIR colouring -> correlated reference
SCENARIOS = ("stationary", "amp_steps", "path_switch", "wav", "feedback")
LIMIT = 1.0 - 2.0 ** -15


@dataclass
class Scenario:
    name: str
    x: np.ndarray        # reference input
    d: np.ndarray        # primary input (signal + path-filtered noise + sensor noise)
    s: np.ndarray        # clean wanted signal (known -> exact metrics)
    events: list         # sample indices of abrupt changes
    h_segs: list         # [(start_index, true_path)] ground-truth coefficients
    n_clip: int = 0      # samples clipped to the fixed-point range



def make_paths(seed=1234):
    """Two fixed ground-truth noise paths: decaying random FIR, unit L2 norm (|tap| < 1)."""
    r = np.random.default_rng(seed)
    out = []
    for _ in range(2):
        h = r.standard_normal(L_TRUE) * np.exp(-np.arange(L_TRUE) / 5.0)
        out.append(h / np.linalg.norm(h))
    return out


def speech_like(n, fs=FS):
    """Deterministic voiced-speech-like signal: 3 harmonics, wobbling pitch, CONSTANT envelope
    (a syllabic envelope was dropped: its power dips dominate settling-time metrics)."""
    t = np.arange(n) / fs
    ph = 2 * np.pi * np.cumsum(140 + 30 * np.sin(2 * np.pi * 0.7 * t)) / fs
    s = sum(a * np.sin(k * ph) for k, a in ((1, 1.0), (2, 0.6), (3, 0.4)))
    return 0.03 * s / np.max(np.abs(s))   # ~ -12 dB SNR vs the reference-noise level


def resample_fft(a, n_out):
    """Band-limited resampling by FFT truncation/zero-padding (no scipy needed)."""
    X = np.fft.rfft(a)
    Y = np.zeros(n_out // 2 + 1, complex)
    m = min(len(X), len(Y))
    Y[:m] = X[:m]
    return np.fft.irfft(Y, n_out) * n_out / len(a)


@lru_cache(maxsize=4)
def load_wav_mono(path, fs_out=FS):
    """Read a 8/16/32-bit PCM WAV with the stdlib, mix to mono, resample to fs_out."""
    with wave.open(path, "rb") as w:
        ch, sw, fr, nf = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(min(nf, 30 * fr))
    if sw not in (1, 2, 4):
        raise ValueError("only 8/16/32-bit PCM WAV supported")
    a = np.frombuffer(raw, {1: np.uint8, 2: np.int16, 4: np.int32}[sw]).astype(float)
    if sw == 1:
        a -= 128
    a = a[: len(a) // ch * ch].reshape(-1, ch).mean(1)
    if fr != fs_out:
        a = resample_fft(a, int(round(len(a) * fs_out / fr)))
    return a


def wav_noise(path, n, seed=0):
    """Unit-RMS noise segment from a real WAV (tiled if short; seed picks the offset)."""
    a = load_wav_mono(path)
    if len(a) < n:
        a = np.tile(a, int(np.ceil(n / len(a))))
    off = (seed * 4000) % max(1, len(a) - n + 1)
    a = a[off:off + n]
    a = a - a.mean()
    return a / a.std()


def make_scenario(name, n=16000, seed=0, wav=None):
    r = np.random.default_rng(seed)
    h1, h2 = make_paths()
    if name == "wav":
        if wav is None:
            raise ValueError("scenario 'wav' needs a WAV path")
        v = wav_noise(wav, n, seed)
    else:
        v = np.convolve(r.standard_normal(n + 10), COLOR)[10:10 + n]
        v /= v.std()
    g, events, segs = np.ones(n), [], [(0, h1)]
    if name == "amp_steps":                     # sudden noise-amplitude changes: x3, then x0.25
        events = [int(.35 * n), int(.6 * n)]
        g[events[0]:], g[events[1]:] = 3.0, 0.25
    elif name == "path_switch":                 # abrupt change of the noise path at n/2
        events, segs = [n // 2], [(0, h1), (n // 2, h2)]
    elif name == "feedback":                    # acoustic howling feedback scenario
        # Speaker output re-enters primary mic through delayed acoustic path with loop gain near 1
        events = []
    v = BASE_RMS * g * v
    nz = np.convolve(v, h1)[:n]
    if name == "path_switch":
        nz[n // 2:] = np.convolve(v, h2)[:n][n // 2:]
    s = speech_like(n)
    d = s + nz + SENSOR_STD * r.standard_normal(n)
    if name == "feedback":
        # Recirculating acoustic delay path: delay D=8 samples (~1 ms), loop gain 0.88 (< 1, near singing margin)
        D_fb = 8
        g_fb = 0.88
        d_fb = np.zeros(n, dtype=float)
        for idx in range(n):
            prev = d_fb[idx - D_fb] if idx >= D_fb else 0.0
            d_fb[idx] = d[idx] + g_fb * prev
        d = d_fb
    x = v
    n_clip = int(np.count_nonzero((np.abs(d) > LIMIT) | (np.abs(x) > LIMIT)))
    return Scenario(name, np.clip(x, -LIMIT, LIMIT), np.clip(d, -LIMIT, LIMIT), s, events, segs, n_clip)


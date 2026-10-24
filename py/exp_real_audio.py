"""Real recorded noise and speech evaluation (journal study, simulation of the bit-exact model).

Data: MS-SNSD (Reddy et al., Interspeech 2019, MIT licence), pinned to commit fe61c4b. Four
noise recordings (air conditioner, vacuum cleaner, copy machine, babble) and ten clean
utterances are fetched on first use into data_cache/ (git-ignored) and checked by SHA-256.

Model per seed (8 kHz, 10 s):  x = v + c * s,  d = s + h * v + sensor noise
  v : a noise recording segment (offset chosen by the seed), RMS 0.06 as in py/signals.py
  s : one clean utterance, scaled for 0 dB SNR against h * v at the primary input
  h : a random decaying 16-tap path with unit norm (seeded), as in signals.make_paths
  c : speech crosstalk into the reference: none, or -20 dB relative to s
Only the acoustic path is simulated; noise and speech are real recordings.

Metrics after the 2 s convergence window (final 8 s): noise reduction of the residual noise
(10 log10 P(h*v) / P(e - s)), and STOI and narrow-band PESQ of e against s, compared with
the unprocessed primary d. Fixed point W = 12, L = 32, fair-tuned settings; float shown too.

    python py/exp_real_audio.py              # 20 seeds, writes results/metrics/real_audio_*.csv
"""
import argparse
import csv
import hashlib
import os
import sys
import urllib.request
import wave
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from algos import run_float  # noqa: E402
from experiment_config import FAIR_TUNED_SETTINGS  # noqa: E402
from fixedpoint import FxCfg, run_fixed  # noqa: E402
from signals import BASE_RMS, L_TRUE, SENSOR_STD, resample_fft  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data_cache")
COMMIT = "fe61c4ba0d9ac8dd7e23d719cc79f8947e1dc742"
URL = "https://raw.githubusercontent.com/microsoft/MS-SNSD/" + COMMIT + "/"
FILES = {
    "noise_test/AirConditioner_1.wav": "3fe55d7035d7ef2599841738f818dc4463f5ef983eb4b5fefeee153d8caa2110",
    "noise_test/VacuumCleaner_1.wav": "594c10d5db0f809b695f90199443b81b799fa1b06c09efcac02c1ebff62fda80",
    "noise_test/CopyMachine_1.wav": "43ce2b5e660c0d68dce14aed21050b9cd37b717430144f966ec9abdfada4ad61",
    "noise_test/Babble_1.wav": "d7a64dd995a92f4790308dbff196332585eec502734ac737bfc9e2ac317dacd6",
    "clean_test/clnsp0.wav": "be5c2c6578f085ac3e95bd42fb0cbda8f6f2bbda0d03bb5b19fbe60d67e079f7",
    "clean_test/clnsp1.wav": "53906dc2f3da62041ec81c37c175ad4c6b89b9e444bf3c9e5c4a4b7cecfe3238",
    "clean_test/clnsp2.wav": "1e82b4cc442db91c9f3e4eff2cd06b2bf7def7078cf90cf02b1a0eb6eadb3b4f",
    "clean_test/clnsp3.wav": "b4cfeee9c64713cf16b787aab526472ed0f6d79cb800c8a320121a26cd693d55",
    "clean_test/clnsp4.wav": "2b1c75020eb98baefaf7868de810ea5773453e42314f3d3fe2f283b8b0603549",
    "clean_test/clnsp5.wav": "1c1a8eb5c1cc79947c42ee94438191a01e2e4ebb27a5a7d99ed0c2ba56b70338",
    "clean_test/clnsp6.wav": "a6eb64b70f1b55c768fa6fc133154ff1b9ee73c1add8e69f32bd7bbdd3c582ed",
    "clean_test/clnsp7.wav": "0a2b3284a9f6c80009f03a407c9228a188bbb5e9603d4fc6186835a1f9f73dc3",
    "clean_test/clnsp8.wav": "264a2511c10a395c6b60b7dbb5e9d30c7412b28f1976f09df6c703e7c4fa3dd8",
    "clean_test/clnsp9.wav": "5b499c641f25e3313179fe2a8f8dc7947e47c31b9b702ffd8c65eddcda2be6b6",
}
NOISES = {"air_conditioner": "noise_test/AirConditioner_1.wav", "vacuum": "noise_test/VacuumCleaner_1.wav",
          "copy_machine": "noise_test/CopyMachine_1.wav", "babble": "noise_test/Babble_1.wav"}
SPEECH = [f"clean_test/clnsp{i}.wav" for i in range(10)]
FS, SECONDS, SKIP_S, L = 8000, 10.0, 2.0, 32
CROSSTALK = {"none": 0.0, "-20dB": 10 ** (-20 / 20)}
ALGOS = ("lms", "nlms", "nlms_shift")


def fetch():
    for rel, sha in FILES.items():
        path = os.path.join(CACHE, rel)
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            urllib.request.urlretrieve(URL + rel, path)
        got = hashlib.sha256(open(path, "rb").read()).hexdigest()
        if got != sha:
            raise SystemExit(f"{rel}: SHA-256 mismatch ({got})")


def load(rel):
    with wave.open(os.path.join(CACHE, rel), "rb") as w:
        fs, n = w.getframerate(), w.getnframes()
        a = np.frombuffer(w.readframes(n), "<i2").astype(float) / 32768.0
    return resample_fft(a, round(len(a) * FS / fs))


def scenario(noise, crosstalk, seed):
    n = int(SECONDS * FS)
    r = np.random.default_rng(1000 + seed)
    v_all = load(NOISES[noise])
    off = int(r.integers(0, len(v_all) - n))
    v = v_all[off:off + n] - v_all[off:off + n].mean()
    v = BASE_RMS * v / v.std()
    s = load(SPEECH[(seed - 1) % len(SPEECH)])
    s = np.resize(s, n)
    h = r.standard_normal(L_TRUE) * np.exp(-np.arange(L_TRUE) / 5.0)
    h /= np.linalg.norm(h)
    nz = np.convolve(v, h)[:n]
    s = s * np.sqrt(np.mean(nz ** 2) / np.mean(s ** 2))          # 0 dB input SNR
    d = s + nz + SENSOR_STD * r.standard_normal(n)
    x = v + CROSSTALK[crosstalk] * s
    lim = 1.0 - 2.0 ** -15
    return np.clip(x, -lim, lim), np.clip(d, -lim, lim), s, nz


def quality(s, sig):
    from pesq import pesq
    from pystoi import stoi
    k = int(SKIP_S * FS)
    return stoi(s[k:], sig[k:], FS, extended=False), pesq(FS, s[k:], sig[k:], "nb")


def one(job):
    noise, xt, seed, algo, kind = job
    x, d, s, nz = scenario(noise, xt, seed)
    st = FAIR_TUNED_SETTINGS[algo]
    if kind == "float":
        e = run_float(algo, x, d, L, st["mu"], eps=2.0 ** -st["eps_exp"])["e"]
        ovf = 0
    else:
        r = run_fixed(algo, x, d, L, st["mu"], FxCfg(W=12, eps_exp=st["eps_exp"]))
        e, ovf = r["e"], sum(v for k_, v in r["counts"].items() if not k_.startswith("in_"))
    k = int(SKIP_S * FS)
    res = e[k:] - s[k:]
    nr = 10 * np.log10(np.mean(nz[k:] ** 2) / np.mean(res ** 2))
    stoi_e, pesq_e = quality(s, np.asarray(e, float))
    stoi_d, pesq_d = quality(s, d)
    return dict(noise=noise, crosstalk=xt, seed=seed, algo=algo, kind=kind, nr=nr, stoi=stoi_e,
                pesq=pesq_e, stoi_in=stoi_d, pesq_in=pesq_d, ovf=ovf)


def summarise(rows):
    import scipy.stats as stt
    out = []
    keys = sorted({(r["noise"], r["crosstalk"], r["algo"], r["kind"]) for r in rows})
    for noise, xt, algo, kind in keys:
        sub = [r for r in rows if (r["noise"], r["crosstalk"], r["algo"], r["kind"]) == (noise, xt, algo, kind)]
        row = dict(noise=noise, crosstalk=xt, algo=algo, kind=kind, n=len(sub))
        for m in ("nr", "stoi", "pesq", "stoi_in", "pesq_in"):
            v = np.array([r[m] for r in sub])
            ci = stt.t.ppf(0.975, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0.0
            row[m] = round(float(v.mean()), 3)
            row[m + "_ci95"] = round(float(ci), 3)
        row["ovf"] = int(sum(r["ovf"] for r in sub))
        out.append(row)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    a = ap.parse_args(argv)
    fetch()
    jobs = [(nz, xt, s, al, kind) for nz in NOISES for xt in CROSSTALK for s in range(1, a.seeds + 1)
            for al in ALGOS for kind in ("fixed", "float")]
    with ProcessPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(one, jobs, chunksize=4))
    mdir = os.path.join(ROOT, "results", "metrics")
    with open(os.path.join(mdir, "real_audio_raw.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    summ = summarise(rows)
    with open(os.path.join(mdir, "real_audio_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summ[0])); w.writeheader(); w.writerows(summ)
    for r in summ:
        if r["kind"] == "fixed":
            print(f"{r['noise']:15s} xt={r['crosstalk']:6s} {r['algo']:10s} NR={r['nr']:6.2f}+-{r['nr_ci95']:.2f} "
                  f"STOI {r['stoi_in']:.3f}->{r['stoi']:.3f}  PESQ {r['pesq_in']:.2f}->{r['pesq']:.2f} ovf={r['ovf']}")


if __name__ == "__main__":
    main()

"""Real-noise noise reduction with and without speech at the primary input (journal study).

Same scenarios as py/exp_real_audio.py (MS-SNSD noise, no crosstalk, fixed point W = 12, L = 32,
fair-tuned settings). The run is repeated with the speech removed from d, so the filter sees
the same real noise and the same path but nothing else. The difference between the two runs is
the noise reduction lost because the speech at the primary input disturbs the adaptation.

    python py/exp_real_audio_nospeech.py     # 20 seeds, writes results/metrics/real_audio_nospeech.csv
"""
import argparse
import csv
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_real_audio as R  # noqa: E402
from experiment_config import FAIR_TUNED_SETTINGS  # noqa: E402
from fixedpoint import FxCfg, run_fixed  # noqa: E402


def one(job):
    noise, seed, algo, speech = job
    x, d, s, nz = R.scenario(noise, "none", seed)
    if not speech:
        d = d - s
    st = FAIR_TUNED_SETTINGS[algo]
    e = np.asarray(run_fixed(algo, x, d, R.L, st["mu"], FxCfg(W=12, eps_exp=st["eps_exp"]))["e"], float)
    k = int(R.SKIP_S * R.FS)
    res = e[k:] - (s[k:] if speech else 0.0)
    return dict(noise=noise, seed=seed, algo=algo, speech=int(speech),
                nr=10 * np.log10(np.mean(nz[k:] ** 2) / np.mean(res ** 2)))


def main(argv=None):
    import scipy.stats as stt
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    a = ap.parse_args(argv)
    R.fetch()
    jobs = [(nz, s, al, sp) for nz in R.NOISES for s in range(1, a.seeds + 1) for al in R.ALGOS for sp in (1, 0)]
    with ProcessPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(one, jobs, chunksize=4))
    out = []
    for noise in R.NOISES:
        for algo in R.ALGOS:
            row = dict(noise=noise, algo=algo, n=a.seeds)
            for sp, tag in ((1, "speech"), (0, "nospeech")):
                v = np.array([r["nr"] for r in rows if (r["noise"], r["algo"], r["speech"]) == (noise, algo, sp)])
                row["nr_" + tag] = round(float(v.mean()), 3)
                row["nr_" + tag + "_ci95"] = round(float(stt.t.ppf(0.975, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v))), 3)
            row["loss"] = round(row["nr_nospeech"] - row["nr_speech"], 3)
            out.append(row)
            print(f"{noise:15s} {algo:10s} speech {row['nr_speech']:6.2f}  no speech {row['nr_nospeech']:6.2f}  "
                  f"loss {row['loss']:5.2f} dB")
    path = os.path.join(R.ROOT, "results", "metrics", "real_audio_nospeech.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)


if __name__ == "__main__":
    main()

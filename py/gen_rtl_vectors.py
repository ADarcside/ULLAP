#!/usr/bin/env python3
"""Generate extra golden vectors + a regression manifest for the RTL testbench.

Reuses py/fixedpoint.py (run_fixed, write_vec) and py/signals.py unchanged. Nothing is re-implemented here.

  python py/gen_rtl_vectors.py            # writes vectors/rtl/*.{vec,w,flg} and tb/manifest.txt

* The shipped candidate vector sets (the existing `shipped_*` manifest lines, vectors/<algo>_W11_<scenario>) are kept in
  the manifest as they are (after checking that run_fixed still reproduces them bit-for-bit).
* Extra sets cover what the shipped ones never exercise: every saturation point (acc, y, e, g, w), other W, other L,
  small accumulators, quiet reference (P = eps), and path-switch behaviour.
* <prefix>.flg holds the expected sticky saturation flags {w,g,e,y,acc,in} as hex (1 if the Python counter > 0).
  Bit 'in' is not produced by RTL (inputs are already W bits), the testbench masks it.
Manifest line: name algo W L MU_INT K ACC_W prefix(relative to repo root) nsamples
"""
import json
import os
import sys
from typing import Optional

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixedpoint as fp
from algos import shift_k
from fixedpoint import FxCfg, run_fixed
from signals import make_scenario

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALGO_ID = {"lms": 0, "nlms": 1, "nlms_shift": 2}
FLAG_BITS = (("in", 0), ("acc", 1), ("y", 2), ("e", 3), ("g", 4), ("w", 5))   # in sat_flags[5:0]


def flags_of(counts):
    v = 0
    for name, bit in FLAG_BITS:
        if name == "in":
            continue                       # not produced by RTL
        if counts[name] > 0:
            v |= 1 << bit
    return v


def gen(name, algo, W, L, mu, scen, n, xscale=1.0, quiet=0, acc_bits: Optional[int] = None, seed=1, eps_exp=10):
    sc = make_scenario(scen, 16000, seed)
    x = sc.x * xscale
    d = sc.d
    if quiet:                              # silent reference at the start: P = 0 -> Q = eps, large e -> g saturates
        x = x.copy()
        x[:quiet] = 0.0
    cfg = FxCfg(W=W, acc_bits=acc_bits, eps_exp=eps_exp)
    r = run_fixed(algo, x, d, L, mu, cfg)
    pre = os.path.join(ROOT, "vectors", "rtl", name)
    fp.write_vec(pre, r, n)
    # NOTE: sticky flags over the first n samples only: rerun on the truncated input
    r2 = run_fixed(algo, x[:n], d[:n], L, mu, cfg)
    assert np.array_equal(r2["ints"]["e"], r["ints"]["e"][:n])
    with open(pre + ".flg", "w") as f:
        f.write(f"{flags_of(r2['counts']):02X}\n")
    mu_int = int(round(mu * 1024)) if algo != "nlms_shift" else 512
    k = shift_k(mu) if algo == "nlms_shift" else 4
    accw = r["acc_bits"]
    return dict(name=name, algo=ALGO_ID[algo], W=W, L=L, MU_INT=mu_int, K=k, ACC_W=accw,
                prefix=f"vectors/rtl/{name}", n=n, flags=flags_of(r2["counts"]), counts=r2["counts"], eps=eps_exp)


def main():
    os.makedirs(os.path.join(ROOT, "vectors", "rtl"), exist_ok=True)
    S = json.load(open(os.path.join(ROOT, "docs", "data", "summary.json")))
    man = []
    # ---- shipped candidate vectors: verify reproducibility, then list them as-is.
    # The shipped sets are taken from the existing manifest ("shipped_*" lines), NOT from summary.json: summary.json is
    # rewritten by every pipeline run and no longer lists the W11 candidates the shipped vectors were generated from.
    mpath = os.path.join(ROOT, "tb", "manifest.txt")
    shipped = []
    if os.path.exists(mpath):
        for ln in open(mpath):
            t = ln.split()
            if len(t) in (9, 10) and t[0].startswith("shipped_"):
                shipped.append(t)
    if not shipped:
        raise SystemExit("tb/manifest.txt has no 'shipped_*' entries; cannot verify/list the shipped vector sets")
    for name, algo_id, W, L, mu_int, K, _acc, prefix, n, *_e in [t[:9] for t in shipped]:
        al = {v: k for k, v in ALGO_ID.items()}[int(algo_id)]
        W, L, mu_int, K, n = int(W), int(L), int(mu_int), int(K), int(n)
        scen = name.split(f"_W{W}_", 1)[1]
        mu = (2.0 ** -K) if al == "nlms_shift" else mu_int / 1024.0
        sc = make_scenario(scen, S["n"], 1)
        r = run_fixed(al, sc.x, sc.d, L, mu, FxCfg(W=W))
        rows, w = fp.read_vec(os.path.join(ROOT, prefix), W)
        I = r["ints"]
        ref = np.stack([I["x"][:n], I["d"][:n], I["y"][:n], I["e"][:n]], 1)
        assert np.array_equal(rows, ref) and np.array_equal(w, I["W"][n - 1]), f"shipped vector mismatch {prefix}"
        man.append(dict(name=name, algo=int(algo_id), W=W, L=L, MU_INT=mu_int, K=K, ACC_W=r["acc_bits"],
                        prefix=prefix, n=n, flags=0, counts=r["counts"], eps=10))
    # ---- extra sets
    X = [
        # name              algo          W   L   mu      scenario       n     xscale quiet acc_bits
        ("lms_W8_L16",      "lms",        8,  16, 0.5,    "stationary",  1500, 1.0,   0,    None),
        ("nlms_W12_L8",     "nlms",       12, 8,  0.05,   "stationary",  1500, 1.0,   0,    None),
        ("shift_W16_L32_k3", "nlms_shift", 16, 32, 0.125,  "path_switch", 2000, 1.0,   0,    None),
        ("lms_W11_sat_w",   "lms",        11, 32, 2.0,    "stationary",  1500, 4.0,   0,    None),
        ("nlms_W11_sat_g",  "nlms",       11, 32, 0.3,    "stationary",  1500, 1.0,   400,  None),
        ("nlms_W11_sat_in", "nlms",       11, 32, 0.3,    "amp_steps",   1500, 8.0,   0,    None),
        ("lms_W11_acc18",   "lms",        11, 32, 0.5,    "stationary",  3000, 1.0,   0,    18),
        ("shift_W11_acc18", "nlms_shift", 11, 32, 0.0625, "stationary",  3000, 1.0,   0,    18),
        ("lms_W20_L32",     "lms",        20, 32, 0.5,    "path_switch", 1500, 1.0,   0,    None),
        ("nlms_W16_L32",    "nlms",       16, 32, 0.05,   "stationary",  1500, 1.0,   0,    None),
        ("shift_W11_sat_w", "nlms_shift", 11, 32, 0.5,    "stationary",  1500, 0.05,  0,    None),
        ("nlms_W11_sat_wg", "nlms",       11, 32, 0.5,    "stationary",  1500, 0.05,  0,    None),
        ("nlms_W11_L5",     "nlms",       11, 5,  0.1,    "stationary",  1000, 1.0,   0,    None),
        # Focused edge-case configurations
        ("lms_W11_L2",      "lms",        11, 2,  0.5,    "stationary",  1000, 1.0,   0,    None),
        ("nlms_W11_L2",     "nlms",       11, 2,  0.1,    "stationary",  1000, 1.0,   0,    None),
        ("shift_W11_L2",    "nlms_shift", 11, 2,  0.0625, "stationary",  1000, 1.0,   0,    None),
        ("shift_W11_k0",    "nlms_shift", 11, 32, 1.0,    "stationary",  1500, 1.0,   0,    None),
        ("shift_W8_k3",     "nlms_shift", 8,  16, 0.125,  "stationary",  1500, 1.0,   0,    None),
        ("lms_W28_L32",     "lms",        28, 32, 0.5,    "stationary",  1000, 1.0,   0,    None),
        ("shift_W28_L32",   "nlms_shift", 28, 32, 0.0625, "stationary",  1000, 1.0,   0,    None),
        ("lms_W30_L2",      "lms",        30, 2,  0.5,    "stationary",  1000, 1.0,   0,    None),
        ("lms_W31_L2",      "lms",        31, 2,  0.5,    "stationary",  1000, 1.0,   0,    62),
        ("lms_W11_acc62",   "lms",        11, 32, 0.5,    "stationary",  1500, 1.0,   0,    62),
        ("lms_W11_acc11",   "lms",        11, 32, 0.5,    "stationary",  1500, 1.0,   0,    11),
        ("shift_W31_L32_rail", "nlms_shift", 31, 32, 0.0625, "stationary",  1000, 4.0,   0,    62),
    ]
    for (nm, al, W, L, m, scen, n, xs, q, ab) in X:
        man.append(gen(nm, al, W, L, m, scen, n, xs, q, ab))
    # ---- Phase-1 operating point (eps_exp, K) = (2, 3) and a conservative alternative (4, 3): W = 10/12/14, three scenarios
    for ee, K in ((2, 3), (4, 3)):
        for W in (10, 12, 14):
            for scen in ("stationary", "amp_steps", "path_switch"):
                man.append(gen(f"shift_e{ee}_k{K}_W{W}_{scen}", "nlms_shift", W, 32, 2.0 ** -K, scen, 3000, eps_exp=ee))
    # low-power stress with the larger eps: quiet reference at start, and a very small reference level
    man.append(gen("shift_e2_k3_W12_quiet", "nlms_shift", 12, 32, 0.125, "stationary", 1500, 1.0, 400, None, eps_exp=2))
    man.append(gen("shift_e2_k3_W12_lowlevel", "nlms_shift", 12, 32, 0.125, "stationary", 1500, 0.02, 0, None, eps_exp=2))
    with open(os.path.join(ROOT, "tb", "manifest.txt"), "w") as f:
        f.write("# name algo W L MU_INT K ACC_W prefix nsamples EPS_EXP   (generated by py/gen_rtl_vectors.py)\n")
        for e in man:
            f.write(f"{e['name']} {e['algo']} {e['W']} {e['L']} {e['MU_INT']} {e['K']} {e['ACC_W']} {e['prefix']} {e['n']} {e['eps']}\n")
    print(f"{'name':20s} algo  W  L   expected flags (w g e y acc)   python counters")
    for e in man:
        fl = e["flags"]
        print(f"{e['name']:28s} {e['algo']} {e['W']:3d} {e['L']:3d}   "
              + " ".join(str((fl >> b) & 1) for b in (5, 4, 3, 2, 1)) + f"   {e['counts']}")


if __name__ == "__main__":
    main()

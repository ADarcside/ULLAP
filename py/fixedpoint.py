"""Integer fixed-point model of the ANC datapath = the Python reference for a later RTL core.

Formats (two's complement, signed):
  x, d, y, e, coefficients : W total bits, F fractional bits (default F = W-1 -> range [-1, 1))
  accumulator (sum w*x)    : acc_bits (default 2W + ceil(log2 L)), 2F fractional bits, final-sum saturation
  power  P = sum x^2       : exact (2F frac bits), P + eps with eps = 2^-eps_exp
  NLMS gain g = mu*e/(P+eps): W+g_extra bits, F frac bits, saturated, rounded integer division
  LMS/NLMS step mu         : constant, mu_int = round(mu * 2^mu_frac)
  NLMS-shift               : step = (e*x) >> (bitlen(P+eps) - F + k), mu = 2^-k
Rounding: 'nearest' (add half-LSB then arithmetic shift, ties toward +inf) or 'floor' (truncate).
Saturation at every narrowing point; each event is counted (overflow counters).
Per-sample order: y = rs(acc, F) -> e = d - y -> update -> w = sat(w + upd).
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np

from algos import windows, shift_k


@dataclass(frozen=True)
class FxCfg:
    W: int = 16
    F: Optional[int] = None
    acc_bits: Optional[int] = None
    rnd: str = "nearest"
    mu_frac: int = 10
    g_extra: int = 4
    eps_exp: int = 10


def rs(v, s, rnd="nearest"):
    """Arithmetic right shift by s with rounding (s <= 0 -> left shift). Works on int and int64 arrays."""
    if s <= 0:
        return v << (-s)
    s = min(s, 62)
    if rnd == "nearest":
        v = v + (1 << (s - 1))
    return v >> s


def sat(v, bits):
    """Saturate to signed `bits`; returns (value, number_of_saturated_elements)."""
    lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    if isinstance(v, np.ndarray):
        return np.clip(v, lo, hi), int(np.count_nonzero((v < lo) | (v > hi)))
    return (hi, 1) if v > hi else (lo, 1) if v < lo else (v, 0)


def quantize(a, W, F):
    return sat(np.floor(np.asarray(a) * (1 << F) + 0.5).astype(np.int64), W)


def run_fixed(algo, x, d, L, mu, cfg):
    W = cfg.W
    F = W - 1 if cfg.F is None else cfg.F
    accb = cfg.acc_bits or 2 * W + (L - 1).bit_length()
    Wg, Fm, rn = W + cfg.g_extra, cfg.mu_frac, cfg.rnd
    assert 0 < F < W and 2 * F >= cfg.eps_exp and F + F - Fm >= 0
    xi, c_x = quantize(x, W, F)
    di, c_d = quantize(d, W, F)
    X = windows(xi, L)
    n = len(xi)
    mu_i = int(round(mu * (1 << Fm))) if algo != "nlms_shift" else 0
    k = shift_k(mu) if algo == "nlms_shift" else 0
    eps_i = 1 << (2 * F - cfg.eps_exp)
    w = np.zeros(L, np.int64)
    Wh, ye, ee = np.empty((n, L), np.int64), np.empty(n, np.int64), np.empty(n, np.int64)
    c = dict(in_x=c_x, in_d=c_d, acc=0, y=0, e=0, g=0, w=0)
    for i in range(n):
        xv = X[i]
        acc_raw = sum(int(wi) * int(xi) for wi, xi in zip(w, xv))
        acc, a = sat(acc_raw, accb)
        c["acc"] += a
        y, a = sat(rs(acc, F, rn), W)
        c["y"] += a
        e, a = sat(int(di[i]) - y, W)
        c["e"] += a
        if algo == "lms":
            upd = rs((mu_i * e) * xv.astype(object), F + Fm, rn).astype(np.int64)
        else:
            Q = sum(int(xi) * int(xi) for xi in xv) + eps_i
            if algo == "nlms":
                num = (mu_i * e) << (F + F - Fm)
                g, a = sat((2 * num + Q) // (2 * Q) if rn == "nearest" else num // Q, Wg)
                c["g"] += a
                upd = rs(g * xv.astype(object), F, rn).astype(np.int64)
            else:
                upd = rs(e * xv.astype(object), Q.bit_length() - F + k, rn).astype(np.int64)
        w, a = sat(w + upd, W)
        c["w"] += a
        Wh[i], ye[i], ee[i] = w, y, e
    s = float(1 << F)
    return dict(e=ee / s, y=ye / s, W=Wh / s, counts=c, acc_bits=accb,
                ints=dict(x=xi, d=di, y=ye, e=ee, W=Wh), W_bits=W)


# ---- test-vector files (shared with the future RTL testbench) --------------------------------
def hexw(v, W):
    return f"{int(v) & ((1 << W) - 1):0{(W + 3) // 4}X}"


def write_vec(prefix, r, nsamp):
    """<prefix>.vec : one line per sample 'x d y_exp e_exp' (hex, two's complement, W bits)
       <prefix>.w   : L lines, coefficients after sample nsamp-1 (hex)."""
    W, I = r["W_bits"], r["ints"]
    with open(prefix + ".vec", "w") as f:
        for i in range(nsamp):
            f.write(" ".join(hexw(I[k][i], W) for k in ("x", "d", "y", "e")) + "\n")
    with open(prefix + ".w", "w") as f:
        f.write("\n".join(hexw(v, W) for v in I["W"][nsamp - 1]) + "\n")


def read_vec(prefix, W):
    def sgn(h):
        v = int(h, 16)
        return v - (1 << W) if v >> (W - 1) else v
    with open(prefix + ".vec") as f:
        rows = [[sgn(t) for t in ln.split()] for ln in f]
    with open(prefix + ".w") as f:
        w = [sgn(t) for t in f.read().split()]
    return np.array(rows, np.int64), np.array(w, np.int64)

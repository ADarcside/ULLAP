"""Floating-point reference adaptive filters (the 'golden' algorithms).

All three share: zero-initialised weights, same filter length L, same input windows,
same error definition e[n] = d[n] - w[n]^T x_n (w updated after e is formed).

  lms        w += mu * e * x
  nlms       w += mu * e * x / (||x||^2 + EPS)
  nlms_shift w += e * x * 2^-(ex + k),  ex = frexp_exponent(||x||^2 + EPS),  mu = 2^-k
             i.e. 1/(||x||^2+EPS) is approximated by 2^-ex  (ex = position of the leading one + 1,
             so ||x||^2 in [2^(ex-1), 2^ex) and 2^-ex is within a factor 0.5..1 of the true 1/P).
             Effective normalised step = 2^-k * P/2^ex  in [mu/2, mu).  No divider, no mu multiplier:
             hardware = leading-one detector + barrel shifter.
"""
import math

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

EPS = 2.0 ** -10      # regulariser, identical for nlms and nlms_shift (real units)


def windows(x, L):
    """Row n = [x[n], x[n-1], ..., x[n-L+1]] (zero history), contiguous."""
    xp = np.concatenate([np.zeros(L - 1, dtype=x.dtype), x])
    return np.ascontiguousarray(sliding_window_view(xp, L)[:, ::-1])


def shift_k(mu):
    k = int(round(-math.log2(mu)))
    if abs(2.0 ** -k - mu) > 1e-12:
        raise ValueError("nlms_shift needs mu = 2^-k")
    return k


def run_float(algo, x, d, L, mu, eps=EPS):
    X = windows(np.asarray(x, float), L)
    n = len(x)
    w, W, e = np.zeros(L), np.empty((n, L)), np.empty(n)
    k = shift_k(mu) if algo == "nlms_shift" else 0
    with np.errstate(all="ignore"):
        for i in range(n):
            xv = X[i]
            ei = d[i] - w @ xv
            if not abs(ei) < 1e3:                       # diverged
                e[i:] = np.nan
                W[i:] = np.nan
                break
            if algo == "lms":
                w += (mu * ei) * xv
            elif algo == "nlms":
                w += (mu * ei / (xv @ xv + eps)) * xv
            else:
                w += math.ldexp(ei, -(math.frexp(xv @ xv + eps)[1] + k)) * xv
            e[i], W[i] = ei, w
    return dict(e=e, y=np.asarray(d) - e, W=W)

"""Width-accurate integer model of rtl/anc_core.v datapath (NOT a simulator of the Verilog text).

Mirrors the RTL's localparam widths, incremental power update, sign-magnitude restoring division
and the S_UPD rounding temporaries (t_half / t_sum wrap at PRW+1 bits) so that RTL-specific
width/overflow hazards can be compared against py/fixedpoint.run_fixed without a Verilog simulator.
`rtl_fix=True` models the corrected S_UPD (update forced to 0 when the shift exceeds PRW).
"""
from math import ceil, log2


def clog2(n):
    return 0 if n <= 1 else (n - 1).bit_length()


def wrap(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def sat(v, bits):
    lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    return (hi, 1) if v > hi else (lo, 1) if v < lo else (v, 0)


def upd_rtl(prod, s, PRW, rtl_fix=True):
    """S_UPD update term: rs(prod, s) as computed with the RTL's PRW+1-bit temporaries (prod is a PRW-bit signed value)."""
    if s <= 0:
        return prod << (-s)
    if rtl_fix and s > PRW:
        return 0
    half = wrap(1 << (s - 1), PRW + 1)          # t_half : reg signed [PRW:0]
    return wrap(prod + half, PRW + 1) >> s      # t_sum  : reg signed [PRW:0]


def run_rtl_model(algo, xi, di, W, L, MU_INT=512, K=4, ACC_W=None, EPS_EXP=2, rtl_fix=True):
    F, CL = W - 1, clog2(L)
    ACC_W = ACC_W or 2 * W + CL
    MUW = clog2(MU_INT + 1) + 1
    GW = W + 4
    AW = max(W + MUW, GW)
    PRW = AW + W
    eps = 1 << (2 * F - EPS_EXP)
    xv, w, pw = [0] * L, [0] * L, 0
    flags = dict(acc=0, y=0, e=0, g=0, w=0)
    ys, es = [], []
    for x, d in zip(xi, di):
        xold = xv[L - 1]
        xv = [x] + xv[:-1]
        if algo != 0:
            pw = pw + x * x - xold * xold
        acc = sum(a * b for a, b in zip(w, xv))
        acc, a = sat(acc, ACC_W); flags["acc"] |= a
        y, a = sat((acc + (1 << (F - 1))) >> F, W); flags["y"] |= a
        e, a = sat(d - y, W); flags["e"] |= a
        ys.append(y); es.append(e)
        Q = pw + eps
        if algo == 0:
            m, s = MU_INT * e, F + 10
        elif algo == 1:
            n2 = 2 * ((MU_INT * e) << (2 * F - 10)) + Q
            q = abs(n2) // (2 * Q)
            r = abs(n2) % (2 * Q)
            g = -(q + (1 if r else 0)) if n2 < 0 else q          # floor via sign-magnitude
            g, a = sat(g, GW); flags["g"] |= a
            m, s = g, F
        else:
            m, s = e, Q.bit_length() - F + K
        nw = []
        for i in range(L):
            prod = m * xv[i]
            upd = upd_rtl(prod, s, PRW, rtl_fix)
            v, a = sat(w[i] + upd, W); flags["w"] |= a
            nw.append(v)
        w = nw
    return dict(y=ys, e=es, w=w, flags=flags)

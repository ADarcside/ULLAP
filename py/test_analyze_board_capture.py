"""Synthetic Signal Tap captures for py/analyze_board_capture.py (no board needed)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_board_capture as abc  # noqa: E402
from board_stimulus import build  # noqa: E402
from rtl_model import run_rtl_model  # noqa: E402


def q(v):
    return np.clip(np.round(v * 2048), -2048, 2047).astype(int)


def fake_capture(path, algo, n=6000, pre=400, hexfmt=False, corrupt=False):
    code, p = abc.ALGOS[algo]
    x, d = build("stationary", n / 8000 + 0.1, 1, True)
    x, d = q(x[:n]), q(d[:n])
    e = np.array(run_rtl_model(code, x.tolist(), d.tolist(), W=12, L=32, **p)["e"])
    rng = np.random.default_rng(0)                    # rows before the reset (adapted state)
    xp, dp, ep = (rng.integers(-500, 500, pre) for _ in range(3))
    xs, ds, es = np.r_[xp, x], np.r_[dp, d], np.r_[ep, e]
    if corrupt:
        es[pre + 3000] += 1
    fmt = (lambda v: format(v & 0xFFF, "03X")) if hexfmt else str
    with open(path, "w") as f:
        f.write("Signal Legend:\n\nData:\n")
        f.write("Sample,rst_sync_2,anc_core:u_anc_core|out_valid,x_reg[11..0],d_reg[11..0],"
                "anc_core:u_anc_core|e_out[11..0]\n")
        for i, (a, b, c) in enumerate(zip(xs, ds, es)):
            f.write(f"{i - pre},1,1,{fmt(a)},{fmt(b)},{fmt(c)}\n")


def fake_timing(path):
    g = np.zeros(20000, int)
    for s in (1000, 7144, 13288):
        g[s] |= 1                      # in_valid strobe
        g[s + 38] |= 2                 # out_valid strobe
        g[s + 1:s + 73] |= 4           # busy
    with open(path, "w") as f:
        f.write("Sample,GPIO[3..0]\n")
        for i, v in enumerate(g):
            f.write(f"{i},{v:X}\n")


def test_bit_exact_and_nr(tmp_path):
    fake_capture(tmp_path / "cap_shift_stationary.csv", "shift")
    fake_capture(tmp_path / "cap_lms_stationary.csv", "lms", hexfmt=True)
    fake_timing(tmp_path / "timing_shift.csv")
    out = tmp_path / "out"
    assert abc.main([str(tmp_path), "--out", str(out)]) == 0
    rows = (out / "board_capture_summary.csv").read_text().splitlines()
    assert len(rows) == 3 and all("bit-exact" in r for r in rows[1:])
    md = (out / "board_capture_summary.md").read_text()
    assert "in_valid period (cycles): 6144" in md and "in_valid to out_valid (cycles): 38" in md
    assert "busy high (cycles): 72" in md
    assert (out / "board_shift_stationary.png").exists()


def test_mismatch_fails(tmp_path):
    fake_capture(tmp_path / "cap_nlms_stationary.csv", "nlms", corrupt=True)
    assert abc.main([str(tmp_path), "--out", str(tmp_path / "out")]) == 1

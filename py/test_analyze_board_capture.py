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


def fake_stp_export(path, algo, n=3000):
    """The layout Quartus 25.1 writes: a Groups section, a 'time unit' header, each bus followed by
    its bits, an all-X first row, and (Transitional qualifier on out_valid) an out_valid = 0 row
    after every sample. The pre-trigger rows start with silence, which the zero-state model
    reproduces by accident until the junk that follows, before the real reset."""
    code, p = abc.ALGOS[algo]
    x, d = build("stationary", n / 8000 + 0.1, 1, True)
    x, d = q(x[:n]), q(d[:n])
    e = np.array(run_rtl_model(code, x.tolist(), d.tolist(), W=12, L=32, **p)["e"])
    rng = np.random.default_rng(1)
    junk = [rng.integers(-500, 500, 400) for _ in range(3)]
    xs, ds, es = (np.r_[np.zeros(300, int), j, v] for j, v in zip(junk, (x, d, e)))
    buses = ("x_reg", "d_reg", "anc_core:u_anc_core|e_out")
    bits = lambda v: ", ".join(str((v >> b) & 1) for b in range(11, -1, -1))
    with open(path, "w") as f:
        f.write("Groups:\n")
        for b in buses:
            f.write(f"{b}[11..0] =, " + ", ".join(f"{b}[{i}]" for i in range(11, -1, -1)) + ",  hex\n")
        f.write("\nData:\ntime unit: ns, anc_core:u_anc_core|out_valid, "
                + ", ".join(f"{b}[11..0], " + ", ".join(f"{b}[{i}]" for i in range(11, -1, -1)) for b in buses)
                + ", rst_sync_2, \n")
        f.write("0, X, " + ", ".join("XXX, " + ", ".join(["X"] * 12) for _ in buses) + ", X, \n")
        t = 1
        for a, b, c in zip(xs, ds, es):
            vals = ", ".join(f"{v & 0xFFF:03X}, {bits(v & 0xFFF)}" for v in (a, b, c))
            for ov in (1, 0):
                f.write(f"{t}, {ov}, {vals}, 1, \n")
                t += 1


def fake_timing(path, split=False):
    g = np.zeros(20000, int)
    for s in (1000, 7144, 13288):
        g[s] |= 1                      # in_valid strobe
        g[s + 38] |= 2                 # out_valid strobe
        g[s + 1:s + 73] |= 4           # busy
    with open(path, "w") as f:
        if split:
            f.write("Sample,GPIO[3],GPIO[2],GPIO[1],GPIO[0]\n")
            for i, v in enumerate(g):
                f.write(f"{i}," + ",".join(str((v >> b) & 1) for b in (3, 2, 1, 0)) + "\n")
        else:
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


def test_quartus_export_layout(tmp_path):
    fake_stp_export(tmp_path / "cap_nlms_wav.csv", "nlms")
    x, d, e, radix = abc.load_capture(tmp_path / "cap_nlms_wav.csv")
    assert radix == "hex" and len(e) == 300 + 400 + 3000
    assert abc.align_and_check(x, d, e, "nlms") == (700, 0)


def test_mismatch_fails(tmp_path):
    fake_capture(tmp_path / "cap_nlms_stationary.csv", "nlms", corrupt=True)
    assert abc.main([str(tmp_path), "--out", str(tmp_path / "out")]) == 1


def test_timing_split_bits(tmp_path):
    fake_timing(tmp_path / "timing_lms.csv", split=True)
    res = abc.analyse_timing(tmp_path / "timing_lms.csv")
    assert res["in_valid period (cycles)"] == 6144 and res["in_valid to out_valid (cycles)"] == 38

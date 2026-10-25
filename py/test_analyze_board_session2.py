"""Synthetic captures for py/analyze_board_session2.py (no board needed)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_board_capture as abc  # noqa: E402
import analyze_board_session2 as s2  # noqa: E402
from board_stimulus import build  # noqa: E402
from rtl_model import run_rtl_model  # noqa: E402
from signals import resample_fft  # noqa: E402


def board_signal(scen, lead=1500, tail=4000, gain=0.8):
    """The 2 s stimulus as the codec would deliver it: resampled to 8138 Hz, scaled, quantised,
    preceded by part of the 1 kHz beep and followed by silence."""
    x, d = build(scen, 2.0, 1, True)
    n = int(round(2.0 * abc.FS))
    t = np.arange(lead) / abc.FS
    tone = 0.25 * np.sin(2 * np.pi * 1000 * t)
    xs = np.r_[tone, gain * resample_fft(x[:16000], n), np.zeros(tail)]
    ds = np.r_[tone, gain * resample_fft(d[:16000], n), np.zeros(tail)]
    return s2.q(xs), s2.q(ds)


def write_cap(path, x, d, e):
    with open(path, "w") as f:
        f.write("Data:\nSample,rst_sync_2,anc_core:u_anc_core|out_valid,x_reg[11..0],d_reg[11..0],"
                "anc_core:u_anc_core|e_out[11..0]\n")
        for i, (a, b, c) in enumerate(zip(x, d, e)):
            f.write(f"{i},1,1,{a},{b},{c}\n")


def test_2s_capture_window_and_reference(tmp_path):
    x, d = board_signal("amp_steps")
    code, p = abc.ALGOS["shift"]
    e = run_rtl_model(code, x.tolist(), d.tolist(), W=12, L=32, **p)["e"]
    write_cap(tmp_path / "cap2s_shift_amp_steps.csv", x, d, e)
    assert s2.main([str(tmp_path), "--out", str(tmp_path / "out")]) == 0
    row = (tmp_path / "out" / "board_session2_summary.csv").read_text().splitlines()[1].split(",")
    assert row[2] == "bit-exact" and abs(float(row[3]) - 1500 / abc.FS) < 0.002 and float(row[4]) > 0.99
    # same signal, only resampled and scaled: board NR close to the 8 kHz model reference
    assert abs(float(row[7])) < 3.0


def test_freeze_switch_found(tmp_path):
    x, d = board_signal("stationary")
    code, p = abc.ALGOS["shift"]
    f = 9000
    e = run_rtl_model(code, x.tolist(), d.tolist(), W=12, L=32,
                      freeze=[0] * f + [1] * (len(x) - f), **p)["e"]
    write_cap(tmp_path / "cap2s_shift_freeze.csv", x, d, e)
    s2.main([str(tmp_path), "--out", str(tmp_path / "out")])
    md = (tmp_path / "out" / "board_session2_summary.md").read_text()
    # updates that round to zero just before the switch make its exact sample ambiguous by a few
    found = int(md.split("freeze on from sample ")[1].split(" ")[0])
    assert "bit-exact" in md and f - 64 <= found <= f


def test_dac_check(tmp_path):
    rng = np.random.default_rng(0)
    e, d = rng.integers(-2048, 2048, 50), rng.integers(-2048, 2048, 50)
    hx = lambda v, b: format(v & ((1 << b) - 1), f"0{b // 4}X")
    for name, byp in (("anc", False), ("byp", True)):
        path = tmp_path / f"dac_{name}.csv"
        with open(path, "w") as f:
            f.write("Data:\ntime unit: ns, anc_core:u_anc_core|out_valid, d_reg[11..0], "
                    "anc_core:u_anc_core|e_out[11..0], dac_left_data[15..0], bypass_latched\n")
            prev = 0
            for i in range(50):
                word = (d[i] << 4) | 5 if byp else prev
                f.write(f"{2 * i}, 1, {hx(d[i], 12)}, {hx(e[i], 12)}, {hx(word, 16)}, {int(byp)}\n")
                prev = d[i] << 4 | 5 if byp else e[i] << 4
                f.write(f"{2 * i + 1}, 0, {hx(d[i], 12)}, {hx(e[i], 12)}, {hx(prev, 16)}, {int(byp)}\n")
        assert s2.dac_check(path, byp)[0] == "PASS"

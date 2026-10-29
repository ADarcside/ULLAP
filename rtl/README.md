# rtl

`anc_core.v` is the noise canceller itself: plain Verilog-2001 (plus `$clog2`), with no vendor
primitives, IP, PLLs or RAM/DSP macros, so it builds on any FPGA flow and any simulator.

The algorithm is chosen with the `ALGO` parameter (0 = LMS, 1 = NLMS, 2 = NLMS-Shift). The
other parameters are the word length `W`, the number of taps `L`, the step (`MU_INT` for LMS and
NLMS, `K` for NLMS-Shift), the regulariser exponent `EPS_EXP` and the accumulator width
`ACC_W`. The comment block at the top of the file spells out the arithmetic, the cycle
schedule and the freeze behaviour.

The core is bit-exact against `py/fixedpoint.py` (`run_fixed`) and `py/rtl_model.py`. At the
tuned settings (W = 12, L = 32) it gives:

| ALGO | Latency, in_valid to out_valid | Busy cycles per sample |
|---|---|---|
| 0, LMS | 35 (L + 3) | 73 |
| 1, NLMS | 37 (L + 5) | 130 |
| 2, NLMS-Shift | 37 (L + 5) | 72 |

These match the GPIO timing measured on the board. The port list and handshake are documented
in [`../docs/rtl_interface.md`](../docs/rtl_interface.md); the board wrapper that connects the
core to the codec lives in [`../quartus/`](../quartus/).

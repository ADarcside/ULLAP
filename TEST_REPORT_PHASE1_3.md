# Test report: Phase 1-3 changes (Verilator 5.49 with -std=c++20, Python 3.13)

| Check | Result |
|---|---|
| Baseline before changes: shipped_nlms_shift W11 (2 sets), Verilator | PASS, lat 35, busy 67 |
| RTL eps/K change only (EPS_EXP=2, K=3 defaults + 20 new vector sets): `tb/run_regression.sh verilator` | 51 of 51 PASS (bit-exact) |
| `tb/run_protocol.sh verilator` (busy-ignore, reset mid-update, 6 configs) after eps change | 6 of 6 PASS |
| Pipelined RTL: `tb/run_regression.sh verilator` | 51 of 51 PASS (bit-exact, flags match) |
| Pipelined RTL: `tb/run_protocol.sh verilator` | 6 of 6 PASS |
| `tb_anc_de2_115_top.v` full wrapper (I2C init, I2S, bypass) | PASS |
| `python -m unittest discover -s py` | 23 tests OK (manifest vectors vs rtl_model.py incl. EPS_EXP column) |

Measured with L = 32 (testbench output): latency LMS 35, NLMS 37, NLMS-shift 37; busy cycles LMS 73, NLMS 124, NLMS-shift 72
(before: 33 / 35 / 35 and 67 / about 120 / 67).

Not tested: Quartus timing and area (Quartus is not available here), Questa, and the board.
Verilator needed `-CFLAGS "-std=c++20 -fcoroutines"` in this environment; that is an environment detail, not a project change.

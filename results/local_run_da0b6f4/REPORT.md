# ULLAP local run report
Date / time: 2026-10-24 23:23 IST
Branch / commit: board-readiness / da0b6f4
Tool versions: Python 3.14.4, Quartus Prime Lite 25.1std.0 Build 1129, Questa Altera Starter FPGA Edition-64 2025.2
Paths used (if not the defaults): Questa license: C:\Users\satvi\questa_lic.dat (overridden from default C:\Users\Lenovo\questa_lic.dat via $env:ANC_QUESTA_LIC)

## Step 1
pytest: 46 passed in 49.38s       audit exit code: 0

## Step 2 Questa
Total: 86/86
T9 line: top_T9_rate                         | PASS | # TB_TOP PASS all_completed test=T9
T10 line: top_T10_gpio                        | PASS | # TB_TOP PASS all_completed test=T10
Failures (if any): none

## Step 3 Builds
| Tag | ALGO/EPS/MU in map.rpt | LEs | Registers | Mult 9-bit | Pins | Setup slack (ns) | Hold slack (ns) | Fmax (MHz) | GPIO pins OK | SHA-256 (first 16 chars) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lms | 0 / 2 / 256 | 1,792 | 1,123 | 4 | 31 | +5.731 | +0.401 | 70.08 | Yes | B9BE384A02967932 |
| nlms | 1 / 0 / 256 | 2,626 | 1,404 | 4 | 31 | +3.263 | +0.401 | 59.75 | Yes | 3A19777344C961ED |
| nlms_shift | 2 / 2 / 512 | 2,610 | 1,186 | 4 | 31 | +2.953 | +0.401 | 58.66 | Yes | 0B223131C80DBDE5 |

Critical warnings: None (0 critical warnings across map, fit, and sta reports for all three builds)

## Step 4 Power
| Tag | Total thermal (mW) | Core dynamic (mW) | Core static (mW) | I/O (mW) | Confidence |
| --- | --- | --- | --- | --- | --- |
| lms | 169.46 | 20.79 | 98.69 | 49.98 | Low: user provided insufficient toggle rate data |
| nlms | 173.15 | 24.36 | 98.75 | 50.04 | Low: user provided insufficient toggle rate data |
| nlms_shift | 172.50 | 23.77 | 98.76 | 49.98 | Low: user provided insufficient toggle rate data |

Gate-level (4b): stopped at vsim netlist elaboration with errors (vopt-7063: Failed to find hierarchical signals 'codec_init_done', 'codec_init_error', 'u_anc_core.w', 'u_anc_core.busy' in post-fit flattened netlist anc_de2_115.vo; and vopt-2732: Module parameter overrides W, L, ALGO, K, EPS_EXP, MU_INT not declared on netlist entity anc_de2_115_top). Stopped per instruction to avoid modifying testbench.

## Step 5
Stimulus files created: 16

## Anything unexpected
1. `pip install -r requirements.txt`: package `pesq` requires Visual C++ 14.0 build tools on Python 3.14, which were absent, causing pesq wheel compilation failure. However, all core packages (`pytest`, `numpy`, `scipy`, `matplotlib`, `pystoi`) were present/installed and all 46 pytest unit tests and verification audit ran and passed without error.
2. Questa license file was located at `C:\Users\satvi\questa_lic.dat` instead of `C:\Users\Lenovo\questa_lic.dat`.
3. In Step 4b, post-fit netlist `anc_de2_115.vo` has flattened internal hierarchy and fixed parameters, preventing `tb/tb_top.v` from resolving hierarchical probes (`dut.u_anc_core.*`, `dut.codec_init_*`) and parameter overrides. Simulation halted as per procedure without editing the testbench.

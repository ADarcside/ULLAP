# rtl/

`anc_core.v` - portable Verilog (2001 + `$clog2`) adaptive noise canceller core: LMS / NLMS / NLMS-shift selected by the
`ALGO` parameter, serial one-multiplier datapath, bit-exact to `py/fixedpoint.py:run_fixed`.
No vendor primitives, IP, PLLs, RAM/DSP macros or constraint files.

**Status: simulated, not synthesised.** Bit-exact agreement with the Python reference was demonstrated in simulation with
Verilator 5.053 on 19 vector sets (see `../docs/verification.md`). No synthesis, resource, timing or hardware result exists.

Interface = `../docs/rtl_interface.md` plus one extra output (`busy`); differences/clarifications are listed in
`../docs/verification.md` section 4. Measured (simulation) cycle counts, L = 32, W = 11:

| ALGO | `out_valid` after edge LAT | `busy` cycles per sample |
|---|---|---|
| LMS | 33 (L+1) | 66 |
| NLMS | 35 (L+3) | 116 (divider length grows with W and `MU_INT`; 131 at W=16) |
| NLMS-shift | 35 (L+3) | 67 |

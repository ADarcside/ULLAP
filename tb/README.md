# tb/

* `tb_anc_core.v` - self-checking testbench (Verilog-2001 + `$value$plusargs`, `$fscanf`). Reads `<prefix>.vec/.w[/.flg]`
  (`+vec=<prefix>`), drives `anc_core` one sample at a time (waits for `busy=0`), compares `y_out`/`e_out` of every sample,
  the out_valid count and latency, the final coefficients (hierarchical read of `dut.w[]`) and the sticky saturation flags.
  Prints one `TB_RESULT PASS|FAIL ...` line.
* `manifest.txt` - 19 configurations (6 shipped vector sets + 13 generated stress sets), written by `py/gen_rtl_vectors.py`.
* `run_regression.sh [verilator|iverilog] [name-regex]` - builds and runs every manifest line; exit status 0 only if all pass.
  Only the Verilator path has been run (`../docs/rtl_regression_log.txt`); the Icarus path is untested.

```
python3 py/gen_rtl_vectors.py                 # (re)generate vectors/rtl/* and tb/manifest.txt, re-checks shipped vectors
tb/run_regression.sh verilator                # needs Verilator >= 5 (--binary --timing), a C++ compiler, make
```
Single run by hand (example, NLMS W=11):
```
verilator --binary --timing -Wno-fatal -Wno-lint --top-module tb_anc_core -GW=11 -GL=32 -GALGO=1 -GMU_INT=48 -GK=4 \
  -GACC_W=27 --Mdir build/x -o sim rtl/anc_core.v tb/tb_anc_core.v && build/x/sim +vec=vectors/nlms_W11_stationary
```
Parameters of the testbench must match the vector set (manifest columns: ALGO W L MU_INT K ACC_W).
`$finish(n)` exit codes are not portable between simulators, so scripts must grep the `TB_RESULT` line.

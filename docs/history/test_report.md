# Test report (cloud session, Linux, Python 3.13, numpy; no HDL simulator available)

## Executed and PASSED
| Check | Result |
|---|---|
| `python -I -m py_compile py/*.py` (baseline) | PASS - no syntax errors |
| `python -I -m unittest discover -s py` on baseline | PASS - 18 tests OK (includes the 9-case extended RTL-model verification: 9/9) |
| Same unit-test command on the patched tree (scratch copy) | PASS - 18 tests OK |
| `--help` import check of run_pipeline.py, run_all.py, import_quartus.py | PASS |
| Patched `gen_rtl_vectors.py` run in a scratch copy of the baseline | PASS - exit 0; regenerated `tb/manifest.txt` and every `vectors/rtl/*` and shipped `vectors/*.vec/.w` file are content-identical to the committed ones (only CRLF vs LF differs); all 6 shipped W11 sets re-verified bit-exact |
| Original `gen_rtl_vectors.py` in a scratch copy | CONFIRMED DEFECT - lists W12 LMS shipped set, manifest changes (see change log) |
| Patched `run_questa_regression.py` without Questa | PASS (expected behaviour) - clear "tools not found" message, exit code 1 |
| Static interface read: `anc_de2_115_top` <-> `anc_core`, `i2s_transceiver`, `wm8731_i2c_init` port names/widths | consistent (manual inspection, not a tool run) |

| `unittest discover -s py -p "test_run_questa*.py"` (new, mocked simulator) | PASS - 5 tests: PASS needs rc==0 + explicit marker (manifest and protocol); rc!=0, missing or FAIL marker -> not PASS; existing license vars preserved; explicit `ANC_QUESTA_LIC` wins; default license used only if its file exists |
| Full `unittest discover -s py` after second pass | PASS - 23 tests OK (18 original + 5 new). Lines printed as `[FAIL]` during these tests are the runner's output for deliberately failing mocked cases. |

These tests exercise the runner logic only; they do NOT show that any real Questa simulation passes.

## FAILED
None of the executed checks failed (apart from the intentional confirmation of the original generator defect above).

## NOT run (tools unavailable or out of scope)
- Questa/ModelSim regression (`run_questa_regression.py`, `tb_anc_core`, `tb_anc_protocol`, `tb_anc_de2_115_top`): no `vsim/vlog` here. The shipped `results/metrics/questa_regression_summary.txt` is the user's own earlier run and was not re-verified.
- Verilator / Icarus regression (`tb/run_regression.sh`, `tb/run_protocol.sh`): not installed; Icarus must not be installed per instructions.
- Quartus synthesis/fit/STA, `.sof`, timing closure (known 50 MHz violation), hardware/audio tests, plots/pipeline re-run: excluded.

## Status
Code completed: yes (2 fixes). Python tests: passed. Questa tests: not run here. Quartus not rerun. Timing closure not verified. Hardware not tested.

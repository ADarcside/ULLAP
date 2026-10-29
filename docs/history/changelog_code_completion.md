# Change log - code-level completion pass (cloud session, 2026-10-13)

Baseline: the uploaded `anc_fpga_rtl_audited_8.zip` (SHA-256 25c8e840d280faa6a9942b21ab90f62e58b885843c8d2bbb681e23a113f293e4), kept unmodified.
Scope: code only. No Quartus / timing / plot / golden-vector work.

## Modified files (2) + 1 new test file
| File | Reason |
|---|---|
| `py/gen_rtl_vectors.py` | CONFIRMED BROKEN. It took the "shipped" vector sets from `docs/data/summary.json["candidates"]`, which now lists only one LMS W12 candidate (the file is rewritten by every pipeline run). Running the script would have rewritten `tb/manifest.txt` without 5 of the 6 committed `shipped_*_W11_*` entries and aborted/changed the shipped checks. It now reads the existing `shipped_*` lines of `tb/manifest.txt` (MU_INT, K, W, L, prefix, n), re-verifies each shipped vector set bit-for-bit against `run_fixed`, and keeps them in the manifest. Everything else (extra stress sets, flags, output format) is unchanged. |
| `py/run_questa_regression.py` | Incomplete runner logic: `main()` always exited 0 even when tests failed, so scripts/CI could not detect a failure; and a missing Questa install produced a raw traceback. Now: returns exit code 1 if any test failed (or none ran); tool paths can be overridden with `ANC_VLOG`, `ANC_VSIM`, `ANC_VLIB`, `ANC_QUESTA_LIC` (defaults are the original Windows paths, so behaviour on the original PC is unchanged); a clear error is printed if the tools are not found. **Second pass:** (a) a test is PASS only if the simulator exit code is 0 AND an explicit `TB_RESULT PASS` (manifest) / `TB_PROTO PASS` (protocol) line is printed and no matching FAIL line exists (new `is_pass()`; output format and configurations unchanged; a non-zero exit with a result line is annotated `[simulator exit code N]`); (b) license env: `ANC_QUESTA_LIC` is applied only when explicitly supplied; otherwise any license variable already present in the environment is left untouched; the original `C:\Users\Lenovo\questa_lic.dat` default is used only if that file exists and no license variable is set. |

## New files (3)
- `py/test_run_questa_regression.py` - 5 focused unit tests (mocked; no simulator) for the pass criteria and the license environment; picked up by `unittest discover -s py`.
- `CHANGELOG_CODE_COMPLETION.md` (this file) and `TEST_REPORT.md` - requested deliverables.

## Not changed (verified by checksum against the baseline)
No RTL, testbench, Quartus file/report/.sof, plot, figure, golden vector, dataset, `results/`, `docs/` or `archive/` file was changed.

## Findings left alone (not confirmed defects / out of scope)
- `quartus/README.md` still lists only `anc_de2_115_top.v` and a different project name; `build_quartus.tcl` is the real flow (documentation drift only).
- `anc_de2_115_top.v`: `SW[1]` "Freeze" gates the whole sample strobe (core input stops, output stays latched) rather than only freezing adaptation. May be intentional; changing it is a speculative RTL change -> deferred to a design decision.
- `verify_core.run_verification_suite` (called by the unit tests) rewrites `results/metrics/verification_summary.{csv,json}` (timestamps/timing) on every test run; running the tests therefore dirties a results file. Not changed (it is how the pipeline records results); restore from git/archive if needed.
- `gen_rtl_vectors.py --help` is not an argparse CLI: any invocation regenerates vectors (line endings become LF on Linux; content is identical).
- `test_rtl_model.py` opens `tb/manifest.txt` without closing it (ResourceWarning only).

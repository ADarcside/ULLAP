# Changes: eps/K retuning (Phase 1), RTL operating point (Phase 2), pipelined multiplier path (Phase 3)

## Phase 1 - tuning (docs/phase1_eps_tuning.md)
* `py/algos.py`: `run_float(..., eps=EPS)` takes the regulariser as an argument.
* `py/sweep_eps.py`, `py/confirm_eps.py`: eps_exp x K sweep and shortlist check (CSV in `results/metrics/`).
* Chosen operating point for NLMS-shift: `EPS_EXP = 2`, `K = 3`. Gate A (hybrid power switch): not adopted.

## Phase 2 - RTL operating point
* `rtl/anc_core.v` defaults: `K = 3`, `EPS_EXP = 2` (were 4 and 10). `quartus/anc_de2_115_top.v` has `K = 3` and a new `EPS_EXP = 2` parameter.
* `tb/manifest.txt` has an optional 10th column `EPS_EXP` (default 10 for old lines); `tb/run_regression.sh`,
  `py/run_questa_regression.py`, `py/gen_rtl_vectors.py`, `py/test_rtl_model.py` updated.
* 20 new vector sets (`shift_e2_k3_*`, `shift_e4_k3_*`, quiet and low-level stress). Manifest now has 51 lines.

## Phase 3 - pipelined multiplier path (arithmetic unchanged)
* Multiplier operands and product are registered; the coefficient update is a separate read-round / add-saturate-write
  pipeline. Stages: operand regs -> product reg -> consume (power / accumulate / MU product / rounded update)
  -> write-back. Issue states: S_P0, S_P1, S_MAC, S_MU, S_UPD; new states S_WAIT (drain) and S_MU2 (NLMS divider set-up).
* Latency to `out_valid`: LMS `L+3` (was `L+1`), NLMS and NLMS-shift `L+5` (was `L+3`). `tb/tb_anc_core.v` LAT_EXP updated.
* Busy cycles per sample, L = 32 (measured by the testbench): LMS 73 (was 67), NLMS-shift 72 (was 67), NLMS 124.
* Results are bit-identical to `run_fixed`: see TEST status in `TEST_REPORT_PHASE1_3.md`.
* NOT verified: timing. No Quartus here; the new critical path must be measured by compiling (Phase 4).

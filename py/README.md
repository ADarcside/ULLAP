# py

All the Python: the reference models, the experiments, the regression runners and the tests.
Scripts are meant to be run from the repository root (`python py/<script>.py`); they find
`results/`, `vectors/` and the rest relative to their own location.

## Models

| File | What it is |
|---|---|
| `algos.py` | Floating-point LMS, NLMS and NLMS-Shift, the reference for "how good can it be" |
| `fixedpoint.py` | Integer model of the datapath (`run_fixed`); the RTL is bit-exact against it |
| `rtl_model.py` | Width-accurate model of `rtl/anc_core.v`, used to check board captures |
| `signals.py` | Test scenarios: stationary, amplitude steps, path switch, WAV noise, acoustic feedback |
| `metrics.py` | Noise reduction curves, MSE, SNR and the fixed-versus-float error |
| `experiment_config.py` | Shared settings, tuned parameters and run metadata |

## Main pipeline

| File | What it does |
|---|---|
| `run_pipeline.py` | Tunes, evaluates float and fixed point, sweeps word length, redraws figures 1 to 11 |
| `run_all.py`, `reproduce.py` | Older drivers for the full study and the refinement experiments |
| `visualize.py` | Figure styling and plotting helpers |
| `verify_core.py` | Extended checks of the integer model |
| `gen_rtl_vectors.py` | Writes golden vectors into `vectors/` and the test manifest into `tb/` |

## Journal experiments

| File | Study |
|---|---|
| `exp_wordlength_fair.py` | Word length W = 8 to 16 at the tuned settings (figure 13) |
| `exp_real_audio.py`, `exp_real_audio_nospeech.py` | Real recorded noise and speech from MS-SNSD: NR, STOI, PESQ |
| `exp_paired_stats.py` | Paired per-seed t-test, Wilcoxon and equivalence (TOST) tests |
| `exp_equiv_step.py` | NLMS-Shift as NLMS with a level-dependent step (figure 16) |
| `exp_level_robustness.py` | Sensitivity to input level |
| `power_activity.py` | RTL bit toggles per sample as an energy proxy |
| `power_gate_level.py` | Gate-level power flow: vectors in, energy per sample out |
| `exp_fair_tuning.py`, `exp_pareto_audit.py`, `exp_precision_table.py` | Fair step-size tuning, Pareto audit (figure 12), precision table |

The remaining `exp_*` scripts (`*_task1` to `*_task7`, `exp_*gate_a*`, `exp_*wav*`,
`exp_test_nlms_eps_grid.py`), `sweep_eps.py` and `confirm_eps.py` are the earlier tuning and
refinement studies. Their outputs are in `results/metrics/` and are described in
`results/refinement_report.md` and `docs/phase1_eps_tuning.md`.

## Hardware and board

| File | What it does |
|---|---|
| `run_iverilog_regression.py`, `run_questa_regression.py` | RTL regression (86 tests) on Icarus or Questa |
| `run_full_regression.py` | Regression plus synthesis in one go |
| `run_verilator_lint.py` | Verilator `-Wall` lint with reviewed waivers |
| `import_quartus.py`, `sta_parser.py` | Parse Quartus fit and timing reports into `results/metrics/` |
| `parse_wm8731_rom.py` | Decodes the codec register ROM into `docs/wm8731_config.md` |
| `board_stimulus.py` | Writes the stimulus WAVs played into the board |
| `check_board_capture.py` | Checks one Signal Tap export against the integer model |
| `analyze_board_capture.py`, `analyze_board_session2.py` | Full analysis of board sessions 1 and 2 |
| `make_fig_board.py`, `make_fig_board_level.py` | Figures 14 and 15 |
| `audit_db_numbers.py` | Cross-checks numbers quoted in the markdown files against the result CSVs |

## Tests

```bash
python -m pytest -q py
```

The `test_*.py` files cover the integer model, rounding and saturation, the freeze input,
vector round trips, the report parsers and the board-capture analysis (on synthetic captures,
so no board is needed).

# Board evidence (DE2-115, Signal Tap)

`signaltap_session1_20261026.zip`: session 1, 25 Oct 2026, captured on the authors' bench laptop
(Quartus Prime Lite 25.1std, no RTL change). Contents: `cap_<lms|nlms|shift>_<scenario>.csv`
(instance `cap`, 65,536 rows, Transitional storage qualifier on out_valid, so 32,768 samples,
trigger on the rising edge of `rst_sync_2` = KEY0 release), `timing_<algo>.csv` (GPIO[3:0] at
50 MHz), the capture Tcl script and the operator's REPORT.md. Stimulus: the 6 s noise-only files
from `py/board_stimulus.py make --seconds 6`, played from the laptop into LINE IN.

Reproduce the analysis:

    unzip signaltap_session1_20261026.zip -d /tmp/s1
    python py/analyze_board_capture.py /tmp/s1 --out results/board/session1

Result (`results/board/session1/board_capture_summary.md`): all 12 captures bit-exact against
`py/rtl_model.py` from the reset onward; 8,138.02 Hz sample rate; in_valid to out_valid 38 / 36 / 38
cycles and busy 72 / 73 / 130 cycles for NLMS-Shift / LMS / NLMS.

Bench-laptop files (from branch `bench-laptop-2026-10-26`, commit 6f68be5): `signaltap/REPORT.md`
and `signaltap/capture_script.tcl` (the operator's report and Tcl capture script), `stimulus_6s/`
(the exact 6 s WAVs played in session 1), `quartus/anc_t9.stp` and the Signal Tap assignments in
`quartus/anc_de2_115.qsf`. The 30 s stimulus WAVs (regenerable with `py/board_stimulus.py`) and a
second copy of the session-1 zip were left out. REPORT.md says `analyze_board_capture.py` does not
exist; it was written afterwards in this repo (`py/analyze_board_capture.py`).

Note: with `anc_t9.stp` enabled in the .qsf, every build includes Signal Tap. The resource and
timing figures in the paper's hardware table are for builds without it; remove the
`ENABLE_SIGNALTAP` / `USE_SIGNALTAP_FILE` lines for that build.

## Session 2 (26 Oct 2026)

`signaltap_session2_20261026.zip`: same bench laptop and Signal Tap setup. Contents:
`cap2s_<lms|nlms|shift>_<scenario>.csv` (2 s seed-1 noise-only stimulus = the simulation signal,
played once; 12 captures), `cap2s_shift_freeze.csv` (SW[1] flipped mid-scenario), `dac_anc.csv` and
`dac_bypass.csv` (third instance `dac`: DAC word vs e / d), `timing_soak.csv` (GPIO timing after
10 minutes of looped noise), `photos/led_boot.jpeg` and `photos/led_soak.jpeg`, the operator's
REPORT.md and capture_log.csv, and the bench scripts (`anc_t9_with_dac.stp`, `qsf_dac_section.txt`,
`gen_dac_instance.py`, `capture_script_dac.tcl`, `check_capture_2s.py`, `check_freeze.py`,
`cue_window.ps1`). The REPORT.md freeze line "-2.8 dB in the last 0.25 s of signal" came from a
window in the silence after the stimulus; the corrected figure is in the summary below.

    unzip signaltap_session2_20261026.zip -d /tmp/s2
    python py/analyze_board_session2.py /tmp/s2 --out results/board/session2
    python py/make_fig_board_level.py board_evidence/signaltap_session2_20261026.zip

Result (`results/board/session2/board_session2_summary.md`): all 13 captures bit-exact; board NR is
2.9 to 10.6 dB below the model at the simulation level because the board received x and d about
3 dB lower (-27 dBFS); at the board's level the model matches within 0.2 dB on stationary and
path-switch noise. Freeze, DAC word (ANC and bypass) and the soak timing pass.

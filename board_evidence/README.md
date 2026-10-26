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

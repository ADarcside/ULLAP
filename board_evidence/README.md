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

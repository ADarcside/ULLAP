# ULLAP Signal Tap board capture - REPORT

Date: 2026-10-26. Board: DE2-115 (EP4CE115F29C7), Quartus Prime Lite 25.1std, no RTL changes.

## Captured (all succeeded, first attempt per file after the test run)
- 12 x cap_<shift|nlms|lms>_<stationary|amp_steps|path_switch|wav>.csv (instance cap, 65536 rows each)
- 3 x timing_<shift|nlms|lms>.csv (instance uto_signaltap_1, GPIO[3:0] = {sample_strobe, busy, out_valid, in_valid}, 8192 rows)
- Stimulus: board_evidence/stimulus_6s/*_noise_48k.wav, played to LINE IN via the Windows default device.

## Qualifier mode
Option 2: Transitional storage on out_valid only (file as provided, unchanged). out_valid alternates 1/0 on every stored row, so each CSV has 32768 samples (out_valid=1 rows) = ~4 s of audio, not 8 s. Trigger: rst_sync_2 rising (KEY0 release), position pre.

## Sanity check (check_capture.py)
Every cap CSV: 32768 out_valid=1 samples; x/d/e vary (hundreds of distinct values); rst_sync_2 changes once. e rms is roughly 20-36 LSB vs d rms ~85-140 LSB in all runs.
The shift stationary file was captured twice: the first two attempts (no KEY0 pressed / timeout, and one with no audio playing, silence) were discarded; the kept file has audio.

## Timing of KEY0 vs audio
KEY0 was pressed when an on-screen cue turned green ~0.9-1.9 s after playback start (operator could not hear the beep through the cable). Press timing was by human, so alignment with the calibration beep is approximate.

## Compile summary (params: shift ALGO2/EPS2/MU512/K3; nlms 1/0/256/3; lms 0/2/256/3)
| algo | errors | worst setup slack (ns) | worst hold slack (ns) |
|---|---|---|---|
| shift | 0 | 2.649 | 0.330 |
| nlms | 0 | 3.775 | 0.284 |
| lms | 0 | 5.681 | 0.316 |

## Not done
- py/analyze_board_capture.py does not exist in the repo, so results/board was not generated.
- anc_de2_115.qsf was restored to NLMS-Shift parameters (backups: quartus/*.bak). The board currently runs the LMS bitstream until reprogrammed.
- Nothing committed or pushed.

# claims.md — what this project does and does not claim

Platform: Terasic DE2-115, Cyclone IV E EP4CE115F29C7, Quartus Prime Lite 25.1std.
Algorithms: LMS, NLMS (restoring divider), NLMS-Shift (leading-one detector + barrel shift, no divider).
Common setup: W=12 (Q1.11), L=32 taps, 16,000 samples, bit-exact integer model checked against the RTL.
Base paper: Rodrigo & Buddhika, TIDAC 2024 (LMS, simulation in MATLAB/Vivado, no numeric results to compare against).

Status key:
- RAW = raw script/CSV output was seen by the reviewer in the chat.
- REPORTED = stated in an Antigravity summary; raw output not seen.
- OPEN = not yet measured or verified.

---

## 1. Noise reduction (final window, seeds 1-20, mean [95% CI], dB) — RAW

Each algorithm uses its own fair-tuned setting, selected on unseen tuning seeds 101-103 with the same criterion
(maximise mean final NR over stationary, amp_steps, path_switch; zero overflow).

| Scenario | LMS (mu=0.25) | NLMS (mu=0.25, EPS_EXP=0) | NLMS-Shift (K=3, EPS_EXP=2) |
|---|---|---|---|
| stationary | 22.39 [22.12, 22.66] | 22.28 [22.01, 22.54] | 22.37 [22.11, 22.63] |
| amp_steps | 22.36 [21.72, 23.00] | 24.16 [23.58, 24.73] | 24.33 [23.88, 24.78] |
| path_switch | 18.95 [18.81, 19.09] | 18.53 [18.39, 18.67] | 18.91 [18.76, 19.06] |
| wav | 5.69 [5.66, 5.73] | 5.73 [5.69, 5.76] | 5.46 [5.42, 5.50] |
| feedback | 4.35 | 4.35 | 4.35 |

Claims supported:
- C1. NLMS-Shift ties fair-tuned NLMS on stationary, amp_steps and feedback (overlapping CIs).
- C2. NLMS-Shift ties LMS on stationary, path_switch and feedback.
- C3. NLMS-Shift and NLMS are about 2 dB better than LMS on amp_steps.
- C4. NLMS-Shift is 0.2-0.3 dB worse than NLMS and LMS on wav. The wav recording is a single fixed chord, so the CIs are narrow.
- C5. Feedback does not separate the algorithms (4.35 dB for all).

Claim NOT made: "NLMS-Shift is uniformly better." An earlier 5.7 dB advantage over NLMS on amp_steps came from an under-regularised NLMS and was withdrawn after fair tuning.

## 2. Single operating point (Pareto, seeds 1-20) — RAW

- C6. No LMS step size reaches stationary >= 22.0 dB and amp_steps >= 24.0 dB together (best LMS pairs: mu=0.25 gives 22.39 / 22.36; mu=0.10 gives 16.17 / 24.18).
- C7. NLMS (22.28 / 24.16) and NLMS-Shift (22.37 / 24.33) each reach both at one setting.
- Caveat: the 22/24 thresholds were chosen after seeing the numbers. The frontier figure (fig12) is the evidence, not the pass/fail.
- Consequence: this is an advantage of normalised algorithms over LMS, not of NLMS-Shift over NLMS.

## 3. wav is an operating-point trade-off — RAW

Settings with the best wav result (selected on seeds 101-103, evaluated on seeds 1-20):

| Algorithm | Setting | wav | stationary | amp_steps | path_switch |
|---|---|---|---|---|---|
| LMS | mu=0.125 | 8.69 | 18.29 | 23.86 | 14.78 |
| NLMS | EPS_EXP=-2, mu=0.5 | 8.55 | 18.03 | 24.25 | 14.54 |
| NLMS-Shift | EPS_EXP=0, K=2 | 8.67 | 18.29 | 24.49 | 14.78 |

- C8. About +3 dB on wav costs about 4 dB on stationary and path_switch. No tested setting reached 10 dB on wav.
- C9. At low reference power NLMS-Shift behaves as LMS with a fixed step (identical stationary and path_switch numbers above).

## 4. Hardware (Cyclone IV E, W=12) — RAW (quartus_summary.csv rows)

| | LMS | NLMS | NLMS-Shift |
|---|---|---|---|
| Logic elements | 1,885 | 2,697 | 2,690 |
| Registers | 1,148 | 1,425 | 1,213 |
| 9-bit multipliers | 4 | 4 | 4 |
| Fmax, slow 85C (MHz) | 59.90 | 61.72 | 61.98 |

- C10. All three compile and meet 50 MHz. NLMS-Shift: setup slack +3.867 ns (slow 85C), hold +0.402 ns (slow 85C; fast 0C hold is +0.181 ns). The pre-pipelining design failed at -7.655 ns / 36.16 MHz.
- C11. LMS is about 30% smaller than NLMS-Shift in logic elements. NLMS-Shift and NLMS are about equal in logic elements.
- Power: not measured (vectorless analysis unavailable).

## 5. Timing and throughput (simulation) — REPORTED

| | LMS | NLMS | NLMS-Shift |
|---|---|---|---|
| Input-to-output latency, cycles | 35 | 37 | 37 |
| Busy cycles per sample | 73 | 127 | 72 |

- C12. NLMS-Shift needs 43% fewer busy cycles per sample than NLMS (72 vs 127) with no divider. The codec now runs at 8.138 kHz (R8 = 0x00C, 6,144 cycles per sample at 50 MHz; tb_top T7/T9): busy fractions 1.19% / 2.07% / 1.17%. The earlier 48.83 kHz setting (1,024 cycles) gave 7.1% / 12.4% / 7.0%.
- Claim NOT made: a latency reduction. Input-to-output latency is the same for NLMS and NLMS-Shift. The codec's internal filter delay is not included (the datasheet figures could not be verified).

## 6. Level robustness — RAW

- C13. All three algorithms pass the overflow criterion (rate < 1e-3) only at 1x and 2x reference level. At 0.25x and 0.5x all fail (weight saturation); at 4x all fail (input clipping, 2,323 overflows for NLMS and NLMS-Shift, 13,519 for LMS). At 0.25x LMS and NLMS-Shift are identical. At 4x the final-window NR in results/paper_numbers.csv (nr_final_mean) is 12.1 dB (NLMS-Shift), 11.3 dB (NLMS) and 6.1 dB (LMS). The overflow counts and the 2x / 4x settings quoted here were checked against the committed CSV rows. Metric definitions (docs/results.md): nr_final is the final 25% of samples, nr_all is the whole run, nr_avg is a 256-sample smoothed dB average over the whole run. The level-sweep table in docs/results.md reports nr_avg, so its 4x figures (6.00 / 12.11 / 12.59 dB for LMS / NLMS / NLMS-Shift) differ from the nr_final figures above.
- Claim NOT made: that normalisation gives level robustness.

## 7. Hybrid LMS/NLMS-Shift switch (Gate A) — RAW

- C14. Adoption rule (>= 1.0 dB in at least two scenarios without hurting the others) was not met (1 passing scenario, 3 hurt). The hybrid is not adopted.
- Caveat: the "fixed" mode halves the step relative to the eps floor (shift 14 vs 13), and in stationary and path_switch the filter stayed in fixed mode 100% of the time. The hybrid is reported as not conclusively tested, not as disproven.

## 8. Verification

- C15. Python unit tests: 23 OK — RAW (summary line seen, repo commit d6508ce).
- C16. RTL vs integer model bit-exactness: 57/57 Questa tests pass in the full regression run (394 s, also 23/23 Python tests and a Quartus metrics check) — RAW (summary lines seen, repo commit d6508ce).
- C17. CDC: no internal register is clocked by the codec bit clock (it is sampled as data by 50 MHz flops) — REPORTED.
- C18. Open-source regression (Icarus Verilog 12, `py/run_iverilog_regression.py`): 86/86 pass — 68 core vector sets, 4 protocol, 3 freeze-hold, 11 top-level (T1-T10 incl. new T9 8 kHz rate and T10 GPIO timing). The new T9/T10 have not yet been run in Questa — RAW (this session).
- C19. Verilator 5.020 `-Wall` lint: 0 unwaived warnings (77 waived in 6 reviewed categories, `results/metrics/verilator_lint.txt`) — RAW.
- C20. Python tests: 46 pass (adds Signal Tap checker and board stimulus tests) — RAW.

## 9. Word length at the fair-tuned settings — RAW (`results/metrics/wordlength_fair_summary.csv`, fig13)

- C21. W = 8..16, 20 seeds, loss against the float run of the same algorithm and setting. Worst-scenario mean loss: W = 10: 4.09 / 5.93 / 4.18 dB (LMS / NLMS / NLMS-Shift); W = 11: 1.24 / 1.14 / 0.93 dB; W = 12: 0.26 / 0.39 / 0.27 dB. W = 11 is the smallest W within 3 dB with zero overflow; W = 12 keeps the margin. This replaces known limit 6 below.
- C22. On the chord recording the fixed-point result is better than float at W = 11 and 12 (up to 3.39 dB) and worse at W = 13 (1.27 to 1.29 dB): the wav scenario is word-length sensitive and should not decide W.

## 10. Real recorded noise and speech — RAW (`results/metrics/real_audio_summary.csv`)

- C23. MS-SNSD (pinned commit, SHA-256 checked), 4 noises x 20 seeds, 0 dB input SNR, simulated 16-tap paths, W = 12. Without reference crosstalk: NR 11.65 to 14.90 dB; STOI 0.69-0.78 -> 0.95-0.98; PESQ-NB 1.36-1.54 -> 2.30-2.81. NLMS leads LMS by 0.39 to 0.61 dB, NLMS-Shift trails NLMS by 0.15 to 0.34 dB.
- C24. With speech leakage into the reference at minus 20 dB into the reference: NR drops by 2.3 to 4.6 dB, PESQ by 0.25-0.60, and 18,500 saturation events occur over 19.2 M processed samples.
- Claim NOT made: real acoustic validation. Only the acoustic paths are simulated, but they are simulated.

## 11. Paired statistics — RAW (`results/metrics/paired_stats.csv`)

- C25. Seeds 1-20 re-run reproduce the paper_numbers.csv means exactly. All NLMS-Shift vs NLMS differences are within a TOST equivalence margin of 0.5 dB either way (p < 0.05), though some are non-zero (path_switch +0.38 dB, p = 1.9e-8; wav -0.27 dB). Normalised vs LMS on amp_steps: +1.79 / +1.97 dB, p < 3e-8. This replaces known limit 7.

## 12. Energy proxy — RAW (`results/metrics/power_activity.csv`)

- C26. RTL bit toggles per processed sample at the board rate (clock excluded): LMS 5,668, NLMS 7,146, NLMS-Shift 6,012 (NLMS-Shift 16% fewer than NLMS). A relative proxy only; no mW figure.

---

## Not claimed

- No board measurement exists. All performance and timing claims are from simulation and Quartus reports. OPEN: programme the NLMS-Shift .sof, observe flags, bypass and freeze, measure latency with a scope.
- Real recorded noise and speech are now evaluated (C23-C24) but with simulated acoustic paths; no real two-microphone recording. OPEN.
- Novelty is not claimed. REPORTED related work, from an AI deep-research tool (not read by the author): Pathi et al. 2026, IEEE ICICV (NLMS with leading-one detector, priority encoder and barrel shifter, claims about 50% fewer LUTs and 30% lower latency; abstract only seen), Huang & Yao 2026, Circuits Systems and Signal Processing (binary reciprocal approximation for adaptive IIR NLMS; opened by the tool, different algorithm), Yao & Huang 2024, IEEE TCAS-II (CSD fast-division NLMS; abstract), Zhao et al. 2018, IEEE Access (division-free variable-regularized LMS; opened by the tool), Huang, Yao & Lee 2024, ICCE-Taiwan (LUT reciprocal NLMS; abstract), Oba, Kim & Arai 2006, ISPACS (FPGA LMS/NLMS with bit-shift division; secondary description in Huang & Yao 2026), and a 1996 patent by Ding on eliminating division in NLMS. A "Lee 2024 thesis" could not be found. Full texts of Zhao 2018, Huang, Yao & Lee 2024 and Huang & Yao 2026 were supplied and are summarised in docs/related_work.md (the last two use the same DE2-115 board). OPEN: read Pathi 2026 in full and position the work. Found in this session (abstract level, docs/related_work.md): Garrett et al., ISLPED 2002, already replace the NLMS division by power-of-two operations from leading-zero counts, so the NLMS-Shift step itself is prior art.
- No comparison with the base paper's numbers is possible: it reports no numeric results.
- No measured or Quartus-estimated power (only the toggle proxy C26; flow in docs/power_flow.md). Objective intelligibility/quality (STOI, PESQ) only; no listening test.

## Pending verification before external use

Done (raw output seen): unit tests (23 OK), full regression (57/57), `run_pipeline.py --quick` leaves Figures 1-7 untouched, `reproduce.py --task all` run on the final code exits 0 and leaves results/paper_numbers.csv unchanged (empty git diff), the audit flags a planted wrong number and a planted swapped value.

Known limits:
1. The explanation given for an earlier paper_numbers.csv diff (nr_avg vs nr_all) does not match the diff shown (its direction is reversed, and the cited change is not in the displayed reproduce.py diff). What is relied on is the end state: the regenerated CSV equals the committed CSV, and its level-sweep rows (including 4x) agree with the raw level-sweep output. An earlier committed version of the CSV held stale level-sweep rows from the old tuning.
2. The number audit is a typo guard, not independent verification. It matches numbers by value within metric-specific columns of the repo's own CSVs and Quartus reports (markdown files were removed from its ground-truth pool), so it cannot catch a wrong number that equals another valid number in the same column family. The row-by-row headline-table check was tuned against two planted errors. Coverage of confidence intervals, percentages (43%, 30%) and derived busy fractions is not confirmed.
3. Quartus reports are tracked in results/quartus_reports/ and the audit reads them from there; results/metrics/quartus_summary.csv is the summary. Specification numbers (50 MHz clock, 20.0 ns period, +0.5 / +3.0 ns Gate B targets, the 2,531 LE estimate) are not measured values and are not matched by the audit.
4. Not done: board test (procedure in docs/board_test.md, tools py/check_board_capture.py and py/board_stimulus.py).
5. The audit's allowlist has 66 entries (spec 28, threshold 21, derived 8, historical 9; counts printed in its summary block). docs/related_work.md is excluded from the audit because its numbers are other papers' figures. Historical entries are numbers from earlier runs with no reproducible source. The audit also matches numbers by value across all CSV columns, so a "matched" number can be matched to an unrelated cell.
6. RESOLVED by C21 (wordlength_fair_*.csv, W = 8..16, 20 seeds). Original note: the committed raw sweep (results/metrics/fixed_sweep.csv) has word lengths 8, 10, 12, 14, 16, 20 and 24 only. There are no W=9 or W=11 data points in the repository, so the evidence for choosing W=12 over W=11 (worst-case degradation 2.97 dB against a 3.0 dB threshold, docs/verification.md) cannot be reproduced. An earlier precision table in docs/results.md did not match the raw data and was replaced. The NLMS degradation column uses a differently tuned float reference and is not a pure quantisation loss.
7. RESOLVED by C25 (paired_stats.csv: paired t, Wilcoxon and TOST). Original note: C1 and C2 'ties' mean overlapping 95% CIs, not an equivalence test; paired per-seed differences are not computed (per-seed values exist on disk for 3 seeds only). The 22/24 dB Pareto thresholds were chosen post hoc.

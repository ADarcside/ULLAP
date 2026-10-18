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

- C10. All three compile and meet 50 MHz. NLMS-Shift: setup slack +3.867 ns (slow 85C), hold +0.402 ns. The pre-pipelining design failed at -7.655 ns / 36.16 MHz.
- C11. LMS is about 30% smaller than NLMS-Shift in logic elements. NLMS-Shift and NLMS are about equal in logic elements.
- Power: not measured (vectorless analysis unavailable).

## 5. Timing and throughput (simulation) — REPORTED

| | LMS | NLMS | NLMS-Shift |
|---|---|---|---|
| Input-to-output latency, cycles | 35 | 37 | 37 |
| Busy cycles per sample | 73 | 127 | 72 |

- C12. NLMS-Shift needs 43% fewer busy cycles per sample than NLMS (72 vs 127) with no divider. At fs = 48 kHz (about 1041 cycles at 50 MHz) busy fractions are 7.0% / 12.2% / 6.9%.
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

---

## Not claimed

- No board measurement exists. All performance and timing claims are from simulation and Quartus reports. OPEN: programme the NLMS-Shift .sof, observe flags, bypass and freeze, measure latency with a scope.
- No real recorded noise. Scenarios are synthetic plus one fixed chord recording. OPEN.
- Novelty is not claimed. Related work found by an AI literature search but not read by the author or reviewer: Huang & Yao 2026 (leading-one detector and barrel shifter NLMS), Yao & Huang 2024 (CSD divisors), Zhao et al. 2018 (division-free LMS), Lee 2024 (LUT dividerless NLMS thesis). OPEN: read them and position the work.
- No comparison with the base paper's numbers is possible: it reports no numeric results.
- No power, no real-speech intelligibility, no listening test.

## Pending verification before external use

Done (raw output seen): unit tests (23 OK), full regression (57/57), `run_pipeline.py --quick` leaves Figures 1-7 untouched, `reproduce.py --task all` run on the final code exits 0 and leaves results/paper_numbers.csv unchanged (empty git diff), the audit flags a planted wrong number and a planted swapped value.

Known limits:
1. The explanation given for an earlier paper_numbers.csv diff (nr_avg vs nr_all) does not match the diff shown (its direction is reversed, and the cited change is not in the displayed reproduce.py diff). What is relied on is the end state: the regenerated CSV equals the committed CSV, and its level-sweep rows (including 4x) agree with the raw level-sweep output. An earlier committed version of the CSV held stale level-sweep rows from the old tuning.
2. The number audit is a typo guard, not independent verification. It matches numbers by value within metric-specific columns of the repo's own CSVs and Quartus reports (markdown files were removed from its ground-truth pool), so it cannot catch a wrong number that equals another valid number in the same column family. The row-by-row headline-table check was tuned against two planted errors. Coverage of confidence intervals, percentages (43%, 30%) and derived busy fractions is not confirmed.
3. Quartus reports are tracked in results/quartus_reports/ and the audit reads them from there; results/metrics/quartus_summary.csv is the summary. Specification numbers (50 MHz clock, 20.0 ns period, +0.5 / +3.0 ns Gate B targets, the 2,531 LE estimate) are not measured values and are not matched by the audit.
4. Not done: board test, push to a remote.
5. The audit's allowlist has 55 entries (spec 18, threshold 20, derived 8, historical 9; counts printed in its summary block). Historical entries are numbers from earlier runs with no reproducible source. The audit also matches numbers by value across all CSV columns, so a "matched" number can be matched to an unrelated cell.
6. The committed raw sweep (results/metrics/fixed_sweep.csv) has word lengths 8, 10, 12, 14, 16, 20 and 24 only. There are no W=9 or W=11 data points in the repository, so the evidence for choosing W=12 over W=11 (worst-case degradation 2.97 dB against a 3.0 dB threshold, docs/verification.md) cannot be reproduced. An earlier precision table in docs/results.md did not match the raw data and was replaced. The NLMS degradation column uses a differently tuned float reference and is not a pure quantisation loss.

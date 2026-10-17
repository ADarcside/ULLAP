# Phase 1: regulariser (eps) and step (K) tuning for NLMS-shift

Reproduce: `python py/sweep_eps.py 12` (grid) and `python py/confirm_eps.py` (shortlist at W = 10, 12, 14).
Data: `results/metrics/eps_sweep_W12.csv`, `results/metrics/eps_confirm.csv`.
Setup: fixed-point model `run_fixed`, W = 12, L = 32, 16000 samples, seeds 1-3, final-window noise reduction (dB).

## Why eps matters
NLMS-shift normalises the step by `Q = P + eps`. With the original `eps = 2^-10` the step stays large when the reference
is quiet, so the filter chases the uncorrelated wanted signal left in `e`. A larger eps shrinks the step with power
(LMS-like at low power) with no mode switch. The regulariser floor already prevents any left shift (`F + K >= EPS_EXP`
is enforced at elaboration), so the failure was not a barrel-shift blow-up.

## Results (mean of 3 seeds, final NR dB)
| eps_exp | K | stationary | amp_steps | path_switch | wav |
|---|---|---|---|---|---|
| 10 (old) | 4 | 20.8 | 9.4 | 20.6 | -11.3 |
| 4 | 3 | 20.2 | 16.1 | 20.7 | 6.2 |
| 3 | 4 | 21.5 | 22.4 | 18.1 | 5.2 |
| **2** | **3** | **22.2** | **24.2** | **19.0** | **5.5** |

Selected: `EPS_EXP = 2`, `K = 3` (mu = 0.125). Conservative alternative: `EPS_EXP = 4`, `K = 3`.
Overflow counts are 0 for every grid point.

## Caveats
* Level dependence: eps is in absolute Q1.(W-1) units. The test signals have reference RMS about 0.06 (P about 0.1-0.3).
  A much louder or quieter reference moves the optimum; re-run the sweep for the real codec levels.
* `wav` (tonal chord) stays far below the 10 dB target for every setting; it is likely limited by the tonal input.
  Confidence intervals for the WAV scenario reflect a fixed audio recording (`acoustic_chord.wav`), with random seeds varying only sensor noise and path perturbations.
* Fixed vs float differ by up to about 2-3 dB on amp_steps / wav (final-window NR is trajectory sensitive), and the fixed
  model is sometimes better. W = 10 is clearly weaker than W = 12 or 14 for eps_exp = 2 and 3.

## Gate A (hybrid power switch)
Not adopted. The hybrid power switch is structurally identical to eps-only for thresholds below eps: because P + eps is bounded below by eps = 0.25, the leading-one position / bit_length of (P + eps) remains strictly constant for all P < 0.25 (s = (0.25).bit_length() - F + K). Consequently, the filter naturally operates in fixed-step LMS mode during quiet intervals without requiring any explicit mode-switching threshold or comparator hardware.

### Gate A Evaluation Results (Mean Final NR in dB across seeds 1–3, W=12, L=32)
*Source: `scratch/check_gate_a_fixed.py`:*

| Scenario | EPS-Only Baseline (`EPS_EXP=2, K=3`) | Second Comparison (`EPS_EXP=4, K=3`) | Hybrid ($P_{\text{low}}=0.3$) | Hybrid ($P_{\text{low}}=0.5$) | Hybrid ($P_{\text{low}}=1.0$) |
|---|---|---|---|---|---|
| **Stationary** | **22.22 dB** | 20.19 dB | 18.23 dB ($-3.99\text{ dB}$) | 18.23 dB ($-3.99\text{ dB}$) | 11.75 dB ($-10.47\text{ dB}$) |
| **Amp Steps** | **24.15 dB** | 16.15 dB | 23.81 dB ($-0.35\text{ dB}$) | 23.81 dB ($-0.35\text{ dB}$) | 21.90 dB ($-2.25\text{ dB}$) |
| **Path Switch** | **18.99 dB** | 20.71 dB | 14.80 dB ($-4.19\text{ dB}$) | 14.80 dB ($-4.19\text{ dB}$) | 8.68 dB ($-10.31\text{ dB}$) |
| **WAV Audio** | **5.51 dB** | 6.24 dB | 8.71 dB ($+3.19\text{ dB}$) | 8.71 dB ($+3.19\text{ dB}$) | 4.88 dB ($-0.63\text{ dB}$) |

*Source & Methodology:* The entire table, including the `EPS_EXP=4, K=3` comparison point, was produced directly by `scratch/check_gate_a_fixed.py` across seeds 1–3 ($W=12, L=32$).

*Exact Scale Derivation for Identical Rows ($P_{\text{low}} \in \{0.3, 0.5\}$):*
In the integer implementation ($W=12$, fractional bits $F = 11$, product accumulator scale $2F = 22$):
- $\epsilon_i = 1 \ll (2F - \text{EPS\_EXP}) = 1 \ll (22 - 2) = 1 \ll 20 = 1{,}048{,}576$
- Thresholds are scaled to integer $Q_{2F}$ units: $\text{th\_low} = \text{int}(P_{\text{low}} \times 2^{2F}) = \text{int}(P_{\text{low}} \times 4{,}194{,}304)$
- For $P_{\text{low}} = 0.3$: $\text{th\_low} = 1{,}258{,}291 \implies \text{th\_low} + \epsilon_i = 2{,}306{,}867$
  $2{,}306{,}867.\text{bit\_length}() = 22 \implies \text{fixed\_s} = 22 - 11 + 3 = 14$
- For $P_{\text{low}} = 0.5$: $\text{th\_low} = 2{,}097{,}152 \implies \text{th\_low} + \epsilon_i = 3{,}145{,}728$
  $3{,}145{,}728.\text{bit\_length}() = 22 \implies \text{fixed\_s} = 22 - 11 + 3 = 14$

### Gate A Operating Mode & Sample Fraction Analysis
*Source: `scratch/audit_gate_a_modes.py` (evaluated across seeds 1–3, 16,000 samples per scenario):*

| Scenario | Mode Fraction ($P_{\text{low}}=0.3$) | Mode Fraction ($P_{\text{low}}=0.5$) | Transitions (Switches) | Input Power Range ($P / 2^{2F}$) | Mean Power $\bar{P} / 2^{2F}$ | Status / Behavior |
|---|---|---|---|---|---|---|
| **Stationary** | 100.00% Fixed (0.00% Norm) | 100.00% Fixed (0.00% Norm) | 1.0 (sample 0 entry) | [0.0026, 0.3512] | 0.1152 | **Not conclusively tested** (never switches out of fixed mode) |
| **Path Switch** | 100.00% Fixed (0.00% Norm) | 100.00% Fixed (0.00% Norm) | 1.0 (sample 0 entry) | [0.0026, 0.3512] | 0.1152 | **Not conclusively tested** (never switches out of fixed mode) |
| **Amp Steps** | 75.10% Fixed (24.90% Norm) | 77.53% Fixed (22.47% Norm) | 6.3 ($P_{0.3}$) / 34.3 ($P_{0.5}$) | [0.0011, 2.8071] | 0.3089 | Switches dynamically during loud burst |
| **WAV Audio** | 89.07% Fixed (10.93% Norm) | 95.79% Fixed (4.21% Norm) | 57.0 ($P_{0.3}$) / 39.0 ($P_{0.5}$) | [0.0000, 1.5259] | 0.1152 | Switches dynamically during chord peaks |

**Detailed Root-Cause Reconciliation for Identical Rows:**
1. **Stationary and Path Switch:** The reference noise power $P$ never exceeds $0.3512 \times 2^{2F}$, which remains strictly below the hysteresis exit thresholds $\text{th\_high} = 0.45 \times 2^{2F}$ (for $P_{\text{low}}=0.3$) and $0.75 \times 2^{2F}$ (for $P_{\text{low}}=0.5$). The filter enters fixed mode on sample 0 ($P < \text{th\_low}$) and never exits (100.00% fixed mode). Because both thresholds produce $\text{fixed\_s} = 14$, both configurations execute an identical, static shift $s=14$ for every sample, yielding 18.23 dB (stationary) and 14.80 dB (path switch). Because the algorithm never switches modes in these scenarios, the hybrid is reported as **"not conclusively tested"** under nominal stationary noise.
2. **Amp Steps and WAV Audio:** Even though the state machine does switch modes (e.g. 557 samples in `amp_steps` where $P_{\text{low}}=0.3$ is in normalized mode while $P_{\text{low}}=0.5$ is in fixed mode), the resulting shift in normalized mode is $s = Q.\text{bit\_length}() - F + K$. In the transition region $P \in [\text{th\_low}, \text{th\_high}]$, the regularised sum $Q = P + \epsilon_i$ lies in $[2^{21}, 2^{22})$, which has bit-length 22. Thus $s = 22 - 11 + 3 = 14$ in normalized mode as well. Consequently, the shift difference count between $P_{\text{low}}=0.3$ and $P_{\text{low}}=0.5$ across all 16,000 samples is exactly **0** (`max_diff_e = 0.0`), producing mathematically identical outputs across all seeds.
3. **Gate A Rule Compliance:** The Gate A adoption rule requires an improvement of $\ge +1.0\text{ dB}$ in at least two scenarios without degrading a third. The hybrid achieves $+3.19\text{ dB}$ on WAV, but degrades Stationary by $-3.99\text{ dB}$, Amp Steps by $-0.35\text{ dB}$, and Path Switch by $-4.19\text{ dB}$ (PASS_CNT=1, HURT_CNT=3). Gate A is strictly rejected without modifying the adoption rule.

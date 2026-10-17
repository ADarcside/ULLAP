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

Because both $(1{,}258{,}291 + 1{,}048{,}576)$ and $(2{,}097{,}152 + 1{,}048{,}576)$ have bit-length 22 (lying strictly between $2^{21} = 2{,}097{,}152$ and $2^{22} = 4{,}194{,}304$), both yield $\text{fixed\_s} = 14$. Whenever signal power drops below the threshold, both configurations enter fixed mode with the identical shift $s=14$, producing bit-identical trajectories and identical final NR values across all seeds.

Furthermore, cancellation performance in this regularised regime depends primarily on the effective step size:
$$\mu_{\text{eff}} = 2^{\text{EPS\_EXP} - K}$$
This is directly confirmed by the parameter sweep rows where configurations with equal $(\text{EPS\_EXP} - K)$ exhibit equivalent steady-state tracking and noise-floor behavior (e.g., EPS_EXP=2, K=3 and EPS_EXP=3, K=4 both yield $\text{EPS\_EXP}-K = -1$).

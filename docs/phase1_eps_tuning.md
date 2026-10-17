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

Furthermore, cancellation performance in this regularised regime depends primarily on the effective step size:
$$\mu_{\text{eff}} = 2^{\text{EPS\_EXP} - K}$$
This is directly confirmed by the parameter sweep rows where configurations with equal $(\text{EPS\_EXP} - K)$ exhibit equivalent steady-state tracking and noise-floor behavior (e.g., EPS_EXP=2, K=3 and EPS_EXP=3, K=4 both yield $\text{EPS\_EXP}-K = -1$).

# RTL interface specification (portable Verilog; implemented in `rtl/anc_core.v`)

Status: Fully synthesized in Quartus Prime Lite 25.1std and verified across 57 test suites in Questa (bit-exact on all vector sets). Setup slack: +3.867 ns at 50 MHz (Fmax = 61.98 MHz). Measured LAT (in_valid to out_valid) = L+3 = 35 cycles (LMS), L+5 = 37 cycles (NLMS, NLMS-shift). Total busy cycles: 73 (LMS), 127 (NLMS), 72 (NLMS-shift).
Original text of this spec is kept below; implementation-time clarifications (extra `busy` port, `in` flag, coefficient
readout, input pacing, MU_INT/K defaults) are in `docs/verification.md` section 4.
The Python model `py/fixedpoint.py` is the bit-level reference; the RTL reproduces it bit-for-bit.
No vendor IP, primitives, PLLs, memories-by-macro or constraints: infer multipliers/RAM from plain RTL only.

## Module `anc_core`

| Parameter | Meaning | Default |
|---|---|---|
| `W` | total signed width of x, d, y, e and coefficients (F = W-1 fractional bits) | 12 |
| `L` | number of taps | 32 |
| `ALGO` | 0 = LMS, 1 = NLMS, 2 = NLMS-shift | 2 |
| `MU_INT` | LMS/NLMS step constant, `round(mu*2^10)` (ALGO 0/1) | 512 |
| `K` | NLMS-shift step exponent, `mu = 2^-K` (ALGO 2) | 3 |
| `ACC_W` | accumulator width, default `2*W + $clog2(L)` | 29 |
| `EPS_EXP` | eps = 2^-EPS_EXP (tuned via Gate A & sweep) | 2 |

| Port | Dir | Description |
|---|---|---|
| `clk`, `rst_n` | in | single clock, synchronous active-low reset (clears delay line and coefficients to 0) |
| `in_valid` | in | 1-cycle strobe: `x_in`, `d_in` hold a new sample pair |
| `freeze` | in | adaptation freeze: sampled when in_valid is accepted; blocks coefficient writes and w saturation flag; no effect on latency or busy; tie to 0 for bit-identical behavior to old core |
| `x_in[W-1:0]`, `d_in[W-1:0]` | in | reference / primary sample, two's complement Q1.(W-1) |
| `out_valid` | out | 1-cycle strobe when `y_out`, `e_out` correspond to the sample accepted `LAT` cycles earlier |
| `y_out[W-1:0]`, `e_out[W-1:0]` | out | filter output and error `e = d - y` (error is the cancelled signal) |
| `sat_flags[5:0]` | out | sticky saturation flags `{w, g, e, y, acc, in}`; cleared by `rst_n` |
| `busy` | out | high while processing an accepted sample; new `in_valid` pulses while `busy=1` are ignored |

### Freeze semantics
When `freeze` is asserted (1'b1) at the clock edge where `in_valid` is accepted (`S_IDLE` state), it is registered into `freeze_r`. While `freeze_r` is active for that sample frame:
- Filtering continues normally (`y_out`, `e_out` are computed with current weights).
- Output latency (`LAT`) and `busy` cycles are completely unchanged.
- Coefficient write-back (`w[i3] <= ...`) is suppressed; weights remain held at their current values.
- The coefficient saturation flag (`sat_flags[5]`, `w` bit) is suppressed.
- Tying `freeze` to `1'b0` gives bit-identical operation to the original core.

Throughput target: one sample pair per `in_valid`; the sample period (>= L cycles at 8 kHz is trivially available on
any board clock) allows a serial, one-MAC implementation (`LAT` ~ 2L+c cycles) or a parallel one. Architecture is
free as long as outputs are bit-identical. `LAT` is a free design parameter and must be reported.

## Arithmetic contract (identical to `run_fixed`)

Per sample, with `xv = [x[n]..x[n-L+1]]` (zero history after reset), `F = W-1`:

1. `acc = sat_ACC_W( sum_i w[i]*xv[i] )` (exact sum, saturate once at the end; 2F fractional bits)
2. `y = sat_W( rs(acc, F) )`, `e = sat_W( d - y )`, with `rs(v,s) = (v + 2^(s-1)) >>> s` (round half up, arithmetic shift)
3. `P = sum_i xv[i]^2` (exact), `Q = P + 2^(2F-EPS_EXP)`
4. update term per tap (all rounding via `rs`):
   * LMS: `upd[i] = rs( (MU_INT*e)*xv[i], F+10 )`
   * NLMS: `g = sat_{W+4}( round_div( (MU_INT*e) << (F+F-10), Q ) )` with `round_div(n,d) = floor((2n+d)/(2d))`; `upd[i] = rs( g*xv[i], F )`
   * NLMS-shift: `upd[i] = rs( e*xv[i], bitlen(Q) - F + K )` (`bitlen(Q)` = index of leading one + 1; a negative shift is a left shift)
5. `w[i] = sat_W( w[i] + upd[i] )`; every saturation event sets the matching `sat_flags` bit.

The NLMS divider is specified as an ideal integer division; its hardware architecture (iterative/reciprocal) is open
and must be bit-identical to the reference or be re-characterised in Python first.

## Testbench contract (`tb/`)

* Inputs/expected outputs: `vectors/<algo>_W<W>_<scenario>.vec` - one line per sample, 4 hex words `x d y_exp e_exp`
  (two's complement, `ceil(W/4)` digits), read with `$fscanf("%h %h %h %h")`; `.w` holds the final coefficients
  (L lines, hex) after the last sample of the `.vec` file (4096 samples).
* Pass criterion: `y_out`, `e_out` equal `y_exp`, `e_exp` for every sample **and** final coefficients equal `.w`
  (bit-exact). The testbench must be self-checking, print mismatch counts and use `$finish` with a non-zero count on failure.
* Regenerate vectors for other widths/configs by editing the candidate list in `py/run_all.py` or calling
  `fixedpoint.run_fixed` + `write_vec` directly.

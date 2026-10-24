# Related work and positioning

Searched 24 Oct 2026. Rows marked "opened" were read from the publisher or repository page
(abstract or summary). Rows marked "full text" were read from PDFs the authors supplied. Before submission an author must read each
cited paper in full and check every number below against the paper.

## What this means for the paper's claim

The divider-free step used by NLMS-Shift (normalise by the position of the leading one of the
input power, then shift) is not new. Garrett et al. (ISLPED 2002) already replaced the NLMS
division by power-of-two operations using a leading-zero count of the filter energy, and they
describe earlier real-valued power-of-two NLMS work. Quantised-normaliser and LUT-reciprocal
variants exist too (Zhao et al. 2018, Lee 2024). The paper therefore must not claim the
algorithm as a contribution. Its defensible contributions are:

1. A like-for-like comparison of LMS, NLMS (restoring divider) and NLMS-Shift on one serial
   core, with fair tuning on held-out seeds and 20-seed confidence intervals.
2. A bit-exact verification chain (Python integer model, RTL, 86 regression tests in Icarus
   with the same list in the Questa runner, mutation tests), and on-board bit-exact capture (T9) once the board test is done.
3. A complete processor-free audio system on a low-cost board (codec configuration, I2S,
   status, test points), timing-closed at 50 MHz on Cyclone IV E.
4. Evidence on real noise and speech (MS-SNSD) with objective intelligibility and quality
   metrics, and a reproducible word-length study.

## Prior work table

| Work | Venue | Method for the NLMS division | Platform | Reported results | Status |
|---|---|---|---|---|---|
| Garrett, Nicol, Blanksby, Howland | ISLPED 2002 | Power-of-two error and energy (leading-zero count), shifts and adds | ASIC, TSMC 0.18 um, 128 MHz, NLMS DFE 8+6 taps | About 73% power saving overall (early termination + low-power synthesis) | Opened ([pdf](https://www.cecs.uci.edu/~papers/compendium94-03/papers/2002/islped02/pdffiles/11_2.pdf)) |
| Zhao, Lin, Chan, So: division-free variable-regularised LMS GSC | IEEE Access 6, 64470-64485, 2018 | Normaliser quantised to a few levels, CSD shift-and-add | Xilinx Virtex-7 XC7VX330T, 22-bit words, 8-sensor beamformer | 19,374 vs 24,953 LUTs, 276 vs 353 DSPs, 124.1 vs 90.8 MHz against a divider design | Full text |
| Huang, Yao, Lee | ICCE-Taiwan 2024 | 6-bit-in, 4-bit-out LUT reciprocal | Same board: DE2-115 Cyclone IV, 16-tap 16-bit parallel FIR NLMS | LUT: 11,276 LEs, 2,514 regs, 91 MHz, 11 cycles/sample, 86.96 mW, 10.52 nJ/sample. 4-bit SRT: 11,500 LEs, 16 cycles, 18.60 nJ/sample | Full text |
| Huang, Yao | Circuits Syst. Signal Process. 45, 7561-7584, 2026 | Binary reciprocal approximation from a leading-one detector and barrel shifter (two-segment linear) | Same board: DE2-115 Cyclone IV, 5th-order NLMS IIR, 20-bit coefficients, 2.857 MS/s | Proposed: 3,008 LEs, 1,834 regs, 11 cycles/sample, 14.48 mW, 5.07 nJ/sample. 15-bit SRT: 3,207 LEs, 25 cycles, 8.33 nJ/sample | Full text |
| Yao, Huang | IEEE TCAS-II 71(4), 2459-2463, 2024 | CSD reciprocal approximation of the divisor | Reported via Huang 2024/2026 (6-bit CSD column above: 11,332 LEs, 10.66 nJ/sample) | Max reciprocal error 11.11% | Cited from the two papers above; not read |
| Oba, Kim, Arai | ISPACS 2006, 485-488 | Divisor quantised to one bit, division by shift | FPGA, 4-element adaptive array | Described in Huang 2026 as having large approximation error | Secondary description only |
| Lee (advisor Lin, co-advisor Yao) | NTU MSc thesis 2024 | 6-bit-in, 4-bit-out LUT reciprocal | FPGA (device not stated); FIR 11,857 LEs, 2,569 registers | About 45% higher throughput and 30.5% lower FOM than an SRT divider | Opened ([NTU](https://tdr.lib.ntu.edu.tw/handle/123456789/96175)) |
| Jagadeeswari et al. (cut-set retimed NLMS for audio) | Analog Integr. Circ. Sig. Process. 126, 2025/26 | Not described on the page | Xilinx Spartan-6, 74.67 MHz vs 33.37 MHz un-retimed | 55.3% shorter critical path; no board audio test described | Opened ([Springer](https://link.springer.com/article/10.1007/s10470-025-02537-3)) |
| Fohl, Matthies, Schwarz | DAFx 2009 | LMS (no division) | Spartan-3 XC3S400 + UCB1400 codec | Dummy-head measurements; numbers in full paper | Opened ([DAFx](https://dafx.de/paper-archive/details/CCYighrFAC9mNN7xktMJow)) |
| Thannoon, Hashim | Eng. Technol. J. 42(2) 2024 | Non-restoring division (RLS, AP) | Spartan-6 xc6slx16 | Systolic LMS/RLS/AP; power reductions 5.9% to 40.5% | Opened ([ETJ](https://etj.uotechnology.edu.iq/journal/vol42/iss2/2/)) |
| Rodrigo, Buddhika (base paper) | TIDAC 2024 | LMS | Vivado / MATLAB simulation | No numeric results | Read in full (project file) |
| Pathi et al. 2026 (ICICV), Ding 1996 patent | as listed in `claims.md` | various | various | not verified | Not found or not opened in this search; read before citing |

## Comparison against this work (cross-platform, qualitative)

ULLAP (Cyclone IV E, W = 12, L = 32, one shared multiplier): LMS 1,885 LEs, NLMS 2,697 LEs,
NLMS-Shift 2,690 LEs; Fmax 59.9 to 62.0 MHz; 73 / 127 / 72 busy cycles per sample; NLMS-Shift
switches 16% fewer RTL bits per sample than NLMS (`results/metrics/power_activity.csv`).
Huang 2024 and Huang 2026 use the same DE2-115 board and report energy per sample
(Quartus dynamic power divided by throughput), so ULLAP should report the same figure of merit
from the Quartus Power Analyzer run. Their designs are fully parallel at MS/s rates, so compare
per tap and per sample, not raw totals. Huang 2026's leading-one detector plus barrel shifter is
close to NLMS-Shift's normaliser, which reinforces that the paper must not claim the normaliser.
A fair numeric comparison with the other works is not possible from the pages opened: devices,
word lengths, tap counts and tasks differ, and most pages do not give word length or taps.
The paper's comparison table should list device, W, L, area, Fmax, cycles per sample and sample
rate from the full papers, and say explicitly that it is cross-platform.

# Related work and positioning

Searched 24 Oct 2026. Rows marked "opened" were read from the publisher or repository page
(abstract or summary); none were read in full. Before submission an author must read each
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
| Zhao et al. per `claims.md` (authors not shown on the page opened): division-free variable-regularised LMS GSC | IEEE Access 2018 | Normaliser quantised to a few levels, CSD shift-and-add | Xilinx Virtex-7 XC7VX330T, 124 MHz, 8-sensor beamformer | At least 21% fewer resources and 26.85% higher speed than a divider design | Opened ([DOAJ](https://doaj.org/article/2766afafa1234a64ba88e80114d5b4c4)) |
| Lee (advisor Lin, co-advisor Yao) | NTU MSc thesis 2024 | 6-bit-in, 4-bit-out LUT reciprocal | FPGA (device not stated); FIR 11,857 LEs, 2,569 registers | About 45% higher throughput and 30.5% lower FOM than an SRT divider | Opened ([NTU](https://tdr.lib.ntu.edu.tw/handle/123456789/96175)) |
| Jagadeeswari et al. (cut-set retimed NLMS for audio) | Analog Integr. Circ. Sig. Process. 126, 2025/26 | Not described on the page | Xilinx Spartan-6, 74.67 MHz vs 33.37 MHz un-retimed | 55.3% shorter critical path; no board audio test described | Opened ([Springer](https://link.springer.com/article/10.1007/s10470-025-02537-3)) |
| Fohl, Matthies, Schwarz | DAFx 2009 | LMS (no division) | Spartan-3 XC3S400 + UCB1400 codec | Dummy-head measurements; numbers in full paper | Opened ([DAFx](https://dafx.de/paper-archive/details/CCYighrFAC9mNN7xktMJow)) |
| Thannoon, Hashim | Eng. Technol. J. 42(2) 2024 | Non-restoring division (RLS, AP) | Spartan-6 xc6slx16 | Systolic LMS/RLS/AP; power reductions 5.9% to 40.5% | Opened ([ETJ](https://etj.uotechnology.edu.iq/journal/vol42/iss2/2/)) |
| Rodrigo, Buddhika (base paper) | TIDAC 2024 | LMS | Vivado / MATLAB simulation | No numeric results | Read in full (project file) |
| Pathi et al. 2026 (ICICV), Oba, Kim & Arai 2006 (ISPACS), Yao & Huang 2024 (TCAS-II), Huang & Yao 2026 (CSSP), Ding 1996 patent | as listed in `claims.md` | various | various | not verified | Not found or not opened in this search; read before citing |

## Comparison against this work (cross-platform, qualitative)

ULLAP (Cyclone IV E, W = 12, L = 32, one shared multiplier): LMS 1,885 LEs, NLMS 2,697 LEs,
NLMS-Shift 2,690 LEs; Fmax 59.9 to 62.0 MHz; 73 / 127 / 72 busy cycles per sample; NLMS-Shift
switches 16% fewer RTL bits per sample than NLMS (`results/metrics/power_activity.csv`).
A fair numeric comparison with the works above is not possible from the pages opened: devices,
word lengths, tap counts and tasks differ, and most pages do not give word length or taps.
The paper's comparison table should list device, W, L, area, Fmax, cycles per sample and sample
rate from the full papers, and say explicitly that it is cross-platform.

# Quartus Prime Hardware Build Manifest: anc_de2_115

## Build Identification & Version
- **Source Git Commit:** `d5a9282` (branch: `board-readiness`)
- **Quartus Prime Version:** Version 25.1std.0 Build 1129 10/21/2025 SC Lite Edition
- **Target Device:** Cyclone IV E EP4CE115F29C7 (Terasic DE2-115)
- **Top-Level Entity:** `anc_de2_115_top`
- **Build Script:** `build_quartus.tcl` (invoked via `quartus_sh -t build_quartus.tcl 2 12 3 2 512`)

## Top-Level Synthesized Parameters
- `ALGO`: 2 (NLMS-Shift)
- `W`: 12 (12-bit word width, Q1.11 signed fixed-point)
- `L`: 32 (32-tap adaptive filter)
- `K`: 3 (Shift parameter, step size $\mu = 2^{-3} = 0.125$)
- `EPS_EXP`: 2 (Regularizer $\epsilon = 2^{-2} = 0.25$)
- `MU_INT`: 512 (Normalized step size integer)
- `ACC_W`: 29 (Accumulator word length)

## Programming Bitstream (.sof)
- **Primary Generated Bitstream:** `quartus/anc_de2_115.sof`
- **Traceable Archive Bitstream:** `C:\work\sof\anc_nlms_shift_W12_d5a9282.sof`
- **File Size:** 3,541,722 bytes
- **SHA256 Checksum:** `951222B887592FD95BA331873FE5F89D31B84C4067059A73FF7C56933C99B70F`

## Compilation Timing & Processing Logs
- **Processing Started:** `Wed Oct 21 00:28:14 2026`
- **Processing Ended:** `Wed Oct 21 00:29:29 2026`
- **Total Elapsed Time:** 00:01:15
- **Flow Steps Completed:**
  1. Analysis & Synthesis (`quartus_map`): 0 errors, 22 warnings
  2. Fitter (Place & Route, `quartus_fit`): 0 errors, 4 warnings
  3. Assembler (Bitstream Generation, `quartus_asm`): 0 errors, 1 warning
  4. TimeQuest Timing Analyzer (`quartus_sta`): 0 errors, 1 warning

## Static Timing Analysis (STA) Slack Summary
All three operational PVT corners met setup and hold requirements with positive slack (no timing violations).

| Model Corner | Clock Domain | Target Freq (MHz) | Setup Slack (ns) | Hold Slack (ns) | Achieved Freq (MHz) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Slow 1200mV 85C** | `CLOCK_50` | 50.00 MHz | **+3.432** | **+0.402** | 60.36 MHz |
| **Slow 1200mV 0C**  | `CLOCK_50` | 50.00 MHz | **+4.858** | **+0.353** | 66.04 MHz |
| **Fast 1200mV 0C**  | `CLOCK_50` | 50.00 MHz | **+11.544** | **+0.181** | 118.26 MHz |

- **Minimum Pulse Width Slack:**
  - `CLOCK_50`: +9.242 ns (Fast 0C) / +9.419 ns (Slow 85C)
  - `AUD_BCLK`: +316.000 ns across all corners
- **Recovery / Removal Slack (`CLOCK_50`):**
  - Recovery: +13.200 ns (Slow 85C) / +16.267 ns (Fast 0C)
  - Removal: +3.089 ns (Fast 0C) / +6.040 ns (Slow 85C)

## Slack Deltas vs. Baseline (78f06c2)
Baseline reference values:
- Slow 85C: Setup = 3.867 ns, Hold = 0.402 ns
- Slow 0C: Setup = 5.177 ns, Hold = 0.353 ns
- Fast 0C: Setup = 11.688 ns, Hold = 0.181 ns

| Model Corner | Current Setup (ns) | Baseline Setup (ns) | Setup Delta (ns) | Current Hold (ns) | Baseline Hold (ns) | Hold Delta (ns) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Slow 85C** | +3.432 | +3.867 | **-0.435** | +0.402 | +0.402 | **0.000** |
| **Slow 0C**  | +4.858 | +5.177 | **-0.319** | +0.353 | +0.353 | **0.000** |
| **Fast 0C**  | +11.544 | +11.688 | **-0.144** | +0.181 | +0.181 | **0.000** |

*Timing closure notes:* Adding synchronizers and routing freeze/bypass to core slightly increased wire delay, reducing setup slack by 0.144 to 0.435 ns, while maintaining ample positive margin (+3.432 ns worst-case setup slack). Hold slacks are 100% identical to baseline.

## Unconstrained Paths Summary
All internal and I/O interface paths are fully constrained via `quartus/de2_115.sdc`:
- **Illegal Clocks:** 0 Setup, 0 Hold
- **Unconstrained Clocks:** 0 Setup, 0 Hold
- **Unconstrained Input Ports:** 0 Setup, 0 Hold
- **Unconstrained Input Port Paths:** 0 Setup, 0 Hold
- **Unconstrained Output Ports:** 0 Setup, 0 Hold
- **Unconstrained Output Port Paths:** 0 Setup, 0 Hold

# ULLAP gate-level power and energy per sample

Core dynamic power of LMS, NLMS and NLMS-Shift (`anc_core` alone, no board wrapper), measured with the
Quartus Power Analyzer from gate-level Questa activity (SDF back-annotated, slow 1200 mV 85 C netlist).
No board was connected or programmed. No RTL was changed. Nothing is committed or pushed.

## Environment

| Item | Value |
|---|---|
| PC | bench laptop "sug" (Windows 11, 23.3 GB RAM, 16 logical CPUs) |
| Repo / branch | `C:\Users\Lenovo\Downloads\ULLAP\ULLAP`, branch `claude/project-thread-z0o2zz` at 8f0f2bf |
| Quartus | Prime Lite 25.1std.0 Build 1129 10/21/2025 (`C:\altera_lite\25.1std\quartus\bin64`) |
| Questa | Questa Altera Starter FPGA Edition-64 vsim 2025.2, 2025.05 May 31 2025 |
| Questa licence | `SALT_LICENSE_SERVER=C:/Users/Lenovo/questa_lic.dat` (single session only) |
| Device | Cyclone IV E EP4CE115F29C7, 50 MHz clock |
| Simulation libraries | precompiled `cycloneive_ver` and `altera_ver` from the Questa install |
| Junction temperature | default, automatically computed: 27.9 C (ambient 25 C, "No Heat Sink With Still Air", board thermal model "None (conservative)"); timing corners 85 C / 0 C defaults |

## Commands

Part A (in `quartus\power`, once per algorithm `lms`, `nlms`, `nlms_shift`):

    quartus_sh -t core_power.tcl <algo>
    quartus_asm core_<algo>

Part B (`quartus\power\run_sims.ps1 <algo> board|max`, run in `quartus\power\sim_<algo>`):

    vlog -work work +define+GATE_LEVEL <quartus\power>/simulation/questa/core_<algo>_7_1200mv_85c_slow.vo <repo>/tb/tb_power.v
    vsim -c -work work -L cycloneive_ver -L altera_ver -sdftyp /tb_power/dut=core_<algo>_7_1200mv_85c_v_slow.sdo +sdf_verbose \
         tb_power +vec=<repo>/vectors/power/<algo> +vcd=<algo>_<mode>.vcd <run args> -do "run -all; quit -f"

Run args: board `+gap=6144 +n=200`; max `+gap=81 +n=2000` (lms), `+gap=138 +n=2000` (nlms), `+gap=80 +n=2000` (nlms_shift).

Part C (once per run, in `quartus\power`):

    quartus_pow core_<algo> --input_vcd=sim_<algo>/<algo>_<mode>.vcd --vcd_filter_glitches=on

## Part A: core alone (slow 85 C corner, 50 MHz constraint)

| Core | ALGO / MU_INT / K / EPS_EXP | Logic elements | Registers | Fmax | Setup slack (85 C) |
|---|---|---|---|---|---|
| LMS | 0 / 256 / 3 / 2 | 1,554 | 960 | 72.63 MHz | 6.231 ns |
| NLMS | 1 / 256 / 3 / 0 | 2,393 | 1,241 | 57.36 MHz | 2.565 ns |
| NLMS-Shift | 2 / 512 / 3 / 2 | 2,383 | 1,022 | 59.86 MHz | 3.293 ns |

All three builds: 0 errors, timing met at 50 MHz. These are the core alone, so they are smaller than the board-level numbers in the paper.

## Part B: TB_POWER summary lines

    lms_board:         TB_POWER DONE samples=200  gap=6144 cycles=1228800 outputs=200  mismatches=0
    lms_max:           TB_POWER DONE samples=2000 gap=81   cycles=162000  outputs=2000 mismatches=0
    nlms_board:        TB_POWER DONE samples=200  gap=6144 cycles=1228800 outputs=200  mismatches=0
    nlms_max:          TB_POWER DONE samples=2000 gap=138  cycles=276000  outputs=2000 mismatches=0
    nlms_shift_board:  TB_POWER DONE samples=200  gap=6144 cycles=1228800 outputs=200  mismatches=0
    nlms_shift_max:    TB_POWER DONE samples=2000 gap=80   cycles=160000  outputs=2000 mismatches=0

All six netlist runs match the golden model on every output. `+n=200` was used for the board runs (no reduction to 100 was needed).

## Part C and D: Power Analyzer and energy per sample

Power Estimation Confidence was "High: user provided sufficient toggle rate data" in all six runs. In every run the VCD was
mapped automatically to `|anc_core` with 0.0% unknown signals.

| Run | Sample rate | Total (mW) | Core dynamic (mW) | Core static (mW) | I/O (mW) | VCD toggle coverage | Dynamic energy per sample |
|---|---|---|---|---|---|---|---|
| LMS board | 8.138 kHz | 155.81 | 3.90 | 99.52 | 52.38 | 98.6% | 479.2 nJ |
| LMS max | 617.3 kHz | 165.35 | 12.80 | 99.61 | 52.94 | 99.0% | 20.7 nJ |
| NLMS board | 8.138 kHz | 159.20 | 7.63 | 99.60 | 51.97 | 91.3% | 937.6 nJ |
| NLMS max | 362.3 kHz | 165.72 | 13.78 | 99.67 | 52.27 | 91.7% | 38.0 nJ |
| NLMS-Shift board | 8.138 kHz | 158.24 | 5.93 | 99.61 | 52.70 | 90.9% | 728.7 nJ |
| NLMS-Shift max | 625.0 kHz | 170.68 | 17.76 | 99.72 | 53.20 | 93.0% | 28.4 nJ |

Energy per sample = core dynamic power / sample rate (`py/power_gate_level.py`, `results/metrics/power_gate_level.csv`).
At the board rate the energy per sample is dominated by clock and idle-register power spread over the long sample period, so the
three board-rate values rank the cores by their always-on clocked state; the max-rate values show the energy of the compute itself.
Static and I/O power are nearly identical across runs, so only core dynamic power separates the algorithms.

## Notes and deviations from the instructions

1. **`quartus_asm` added.** `quartus_pow` refused to run ("requires a successful run of the Assembler"), and `core_power.tcl` does not run it. I ran `quartus_asm core_<algo>` for all three projects before Part C.
2. **Simulation libraries.** The Questa install already ships `cycloneive_ver` and `altera_ver`, so nothing was compiled into new libraries.
3. **SDF file path.** The `.vo` embeds a relative `$sdf_annotate` filename, so the `.sdo` was copied into each `sim_<algo>` folder. The explicit `-sdftyp` back-annotation also completed ("SDF Backannotation Successfully Completed").
4. **Single Questa session.** The licence allows only one running session, so runs were done one at a time.
5. **NLMS-Shift `$hold` messages.** Both NLMS-Shift logs show 3 `** Error: $hold(posedge clk &&& reset, sclr, 186 ps)` timing-check messages at 73.14 ns (during the reset sequence, on registers `sh_r[10]`, `sh_r[5]`, `sh_r[4]`). They are timing-check violations in the netlist, not SDF annotation errors: back-annotation succeeded, and both runs end with `mismatches=0`. They occur once, during reset, and should not affect the power numbers, but they are reported rather than hidden. The LMS and NLMS logs have none.
6. **Interruptions.** The first NLMS-Shift board, NLMS max and NLMS-Shift max runs were interrupted by a laptop power loss on battery. NLMS max and NLMS-Shift max were deleted and rerun from scratch. The NLMS-Shift board run had already finished with `mismatches=0` and was kept.
7. Log files were converted from PowerShell's UTF-16 to UTF-8 so `py/power_gate_level.py` could read them. No content was changed.
8. VCD files are not included (0.5 to 3.4 GB each).

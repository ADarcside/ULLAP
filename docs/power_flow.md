# Power estimation flow

Two levels of evidence, labelled differently in the paper.

## 1. Switching-activity proxy (done, simulation)

`python py/power_activity.py` streams 1,000 samples through `anc_core` at the board rate (one
sample every 6,144 cycles) for each algorithm at its board setting and counts RTL bit toggles of
every net and register except the clock (`results/metrics/power_activity.csv`). Toggles per
sample rank the architectures by dynamic energy per sample. They ignore capacitance, glitches,
clock-tree and static power, so they are a relative measure only.

## 2. Quartus Power Analyzer with gate-level activity (needs Quartus + Questa on your PC)

The full board design cannot be used: its gate-level netlist is flattened, so `tb/tb_power.v`
cannot bind to the core inside it. The flow therefore compiles `anc_core` on its own.

1. `python py/power_gate_level.py vectors` writes `vectors/power/<algo>.vec` (stimulus plus the
   golden `e` of `py/rtl_model.py` at each algorithm's board setting). Already committed.
2. `cd quartus/power` and `quartus_sh -t core_power.tcl <algo>` for `lms`, `nlms`, `nlms_shift`.
   This compiles `anc_core` alone at the board setting and writes a timing-simulation netlist
   (`.vo` and `.sdo`) under `simulation/questa/`.
3. Simulate `tb/tb_power.v` compiled with `+define+GATE_LEVEL` against the `.vo`, the Cyclone IV E
   simulation library (`cycloneive_ver`, from the Questa Intel FPGA precompiled libraries or
   compiled from `quartus/eda/sim_lib/cycloneive_atoms.v`) and the `.sdo` on `tb_power/dut`.
   Two runs per algorithm:
   - `board`: `+gap=6144 +n=200` (the real 8.138 kHz sample rate);
   - `max`: `+gap=81` (LMS), `+gap=138` (NLMS) or `+gap=80` (NLMS-Shift) with `+n=2000`
     (back-to-back samples, a few cycles above the busy cycles).
   The summary line must read `outputs=<n> mismatches=0`; the testbench checks every `e_out`
   against the golden vector.
4. `quartus_pow core_<algo>` with the run's VCD as input file, glitch filtering on, and the VCD
   hierarchy `tb_power/dut` mapped to the top entity. The report's confidence should be high,
   with almost all toggle rates taken from simulation.
5. Save each run as `<algo>_<mode>.pow.rpt` and `<algo>_<mode>.log`, then
   `python py/power_gate_level.py report <dir>` writes `results/metrics/power_gate_level.csv`
   with the dynamic energy per sample: core dynamic power / 8,138 Hz for `board`, and
   core dynamic power x gap / 50 MHz for `max` (comparable with power/throughput figures of merit).

Measured result (27 Oct 2026, bench laptop, Quartus Prime Lite 25.1, Questa 2025.2): all six runs
`mismatches=0`, Power Analyzer confidence High, raw reports and logs in
`results/quartus_reports/power_gate_level/`, table in `results/metrics/power_gate_level.csv`.
Two notes from that run: `quartus_asm` had to be run by hand before `quartus_pow` (now part of
`core_power.tcl`), and the NLMS-Shift netlist logs three `$hold` timing-check messages at 73 ns,
where `tb_power` releases `rst_n` on the clock edge itself; this is before `$dumpvars`, so it is outside
the recorded activity, and every output still matches.

Expected shape (written before the run): Cyclone IV E static power dominates (on the order of 100 mW
for the EP4CE115), and the core's dynamic power is small because the datapath is busy for only
72 to 130 of 6,144 cycles per sample. That is why the paper should report dynamic energy per
sample, not total power, when comparing algorithms.

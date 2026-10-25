# Power estimation flow

Two levels of evidence, labelled differently in the paper.

## 1. Switching-activity proxy (done, simulation)

`python py/power_activity.py` streams 1,000 samples through `anc_core` at the board rate (one
sample every 6,144 cycles) for each algorithm at its board setting and counts RTL bit toggles of
every net and register except the clock (`results/metrics/power_activity.csv`). Toggles per
sample rank the architectures by dynamic energy per sample. They ignore capacitance, glitches,
clock-tree and static power, so they are a relative measure only.

## 2. Quartus Power Analyzer with gate-level activity (needs Quartus + Questa on your PC)

1. Build the project for one algorithm (`docs/board_test.md` section 1).
2. Assignments > Settings > EDA Tool Settings > Simulation: Questa Intel FPGA, Verilog, output
   `simulation/questa`. Run Processing > Start > Start EDA Netlist Writer. This writes
   `anc_de2_115.vo` and an SDF file.
3. Simulate `tb/tb_power.v` against the gate-level core. For a top-level run, simulate `tb/tb_top.v`
   with `+test=T3` against the `.vo` and the Cyclone IV E library (`cycloneive_ver`), and add
   `$dumpvars(0, tb_top.dut)` with `$dumpfile("power.vcd")`. Run for at least 0.5 s of simulated
   time (about 4,000 samples) so idle and active phases are both represented.
4. Assignments > Settings > Power Analyzer Settings: use input file `power.vcd`, entity
   `tb_top|dut`, default toggle rate 12.5 % for nodes not in the file, junction temperature 25 C.
   Run `quartus_pow anc_de2_115 --input_vcd=power.vcd --vcd_filter_glitches=on`.
5. Report from the `.pow.rpt`: total thermal power, core static, core dynamic and I/O power,
   and the confidence metric. Energy per sample = core dynamic power / 8,138 Hz.
6. Repeat for the three bitstreams and add a row per algorithm to the hardware table.

Expected shape (not a measurement): Cyclone IV E static power dominates (on the order of 100 mW
for the EP4CE115), and the core's dynamic power is small because the datapath is busy for only
72 to 127 of 6,144 cycles per sample. That is why the paper should report dynamic energy per
sample, not total power, when comparing algorithms.

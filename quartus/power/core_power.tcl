# =============================================================================
# core_power.tcl: anc_core alone (no board wrapper) for the gate-level power flow
#
#   cd quartus/power
#   quartus_sh -t core_power.tcl <algo>        algo = lms | nlms | nlms_shift
#
# Creates project core_<algo> with top-level entity anc_core at the algorithm's board
# setting (py/power_activity.py CONFIGS), compiles it for the DE2-115 device, and writes
# a Verilog timing-simulation netlist (.vo + .sdo) for Questa under simulation/questa/.
# The ports go to unassigned pins; the paper uses the core dynamic power only, which the
# Power Analyzer reports apart from I/O power. See docs/power_flow.md.
# =============================================================================
load_package flow

set algo [lindex $argv 0]
array set P {
    lms        {0 256 3 2}
    nlms       {1 256 3 0}
    nlms_shift {2 512 3 2}
}
if {![info exists P($algo)]} { puts "usage: quartus_sh -t core_power.tcl lms|nlms|nlms_shift"; exit 1 }
lassign $P($algo) a mu k e

set proj core_$algo
if {[project_exists $proj]} { project_open $proj -force } else { project_new $proj -overwrite }

set_global_assignment -name FAMILY "Cyclone IV E"
set_global_assignment -name DEVICE EP4CE115F29C7
set_global_assignment -name TOP_LEVEL_ENTITY anc_core
set_global_assignment -name VERILOG_FILE ../../rtl/anc_core.v
set_global_assignment -name SDC_FILE core_power.sdc
set_parameter -name W 12
set_parameter -name L 32
set_parameter -name ALGO $a
set_parameter -name MU_INT $mu
set_parameter -name K $k
set_parameter -name EPS_EXP $e

set_global_assignment -name EDA_SIMULATION_TOOL "Questa Intel FPGA (Verilog)"
set_global_assignment -name EDA_OUTPUT_DATA_FORMAT "VERILOG HDL" -section_id eda_simulation
set_global_assignment -name EDA_TIME_SCALE "1 ps" -section_id eda_simulation
set_global_assignment -name EDA_GENERATE_FUNCTIONAL_NETLIST OFF -section_id eda_simulation

set_global_assignment -name POWER_DEFAULT_TOGGLE_RATE 12.5%
set_global_assignment -name POWER_PRESET_COOLING_SOLUTION "NO HEAT SINK WITH STILL AIR"
set_global_assignment -name POWER_BOARD_THERMAL_MODEL "NONE (CONSERVATIVE)"

execute_module -tool map
execute_module -tool fit
execute_module -tool asm   ;# quartus_pow refuses to run without an Assembler result
execute_module -tool sta
execute_module -tool eda
project_close
puts "core_power.tcl: $proj done (ALGO=$a MU_INT=$mu K=$k EPS_EXP=$e)"

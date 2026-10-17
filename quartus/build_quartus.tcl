# =============================================================================
# build_quartus.tcl: Automated Compilation Script for DE2-115 Cyclone IV E
# Run via: quartus_sh -t build_quartus.tcl
# =============================================================================

load_package flow

set project_name "anc_de2_115"

# Create project and overwrite if exists
project_new -overwrite $project_name

# Target Hardware
set_global_assignment -name FAMILY "Cyclone IV E"
set_global_assignment -name DEVICE EP4CE115F29C7
set_global_assignment -name TOP_LEVEL_ENTITY anc_de2_115_top

# Verilog RTL Sources (Exclude Testbenches)
set_global_assignment -name VERILOG_FILE ../rtl/anc_core.v
set_global_assignment -name VERILOG_FILE wm8731_i2c_init.v
set_global_assignment -name VERILOG_FILE i2s_transceiver.v
set_global_assignment -name VERILOG_FILE anc_de2_115_top.v
set_global_assignment -name SDC_FILE de2_115.sdc

# Source Official DE2-115 Pin Assignments
source de2_115_pins.tcl

# Optional Command-Line Top-Level Parameter Overrides
if {$argc >= 1} {
    set algo [lindex $argv 0]
    set_parameter -name ALGO $algo
}
if {$argc >= 2} {
    set w_val [lindex $argv 1]
    set_parameter -name W $w_val
}
if {$argc >= 3} {
    set k_val [lindex $argv 2]
    set_parameter -name K $k_val
}
if {$argc >= 4} {
    set eps_val [lindex $argv 3]
    set_parameter -name EPS_EXP $eps_val
}
if {$argc >= 5} {
    set mu_val [lindex $argv 4]
    set_parameter -name MU_INT $mu_val
}

# Compilation Flow
puts "================================================================="
puts "Starting Quartus Prime Lite Synthesis (Analysis & Synthesis)..."
puts "================================================================="
execute_module -tool map

puts "================================================================="
puts "Starting Quartus Prime Lite Fitter (Place & Route)..."
puts "================================================================="
execute_module -tool fit

puts "================================================================="
puts "Starting Quartus Prime Lite Assembler (SOF Bitstream)..."
puts "================================================================="
execute_module -tool asm

puts "================================================================="
puts "Starting Quartus TimeQuest Timing Analyzer..."
puts "================================================================="
execute_module -tool sta

project_close
puts "================================================================="
puts "Quartus Prime Lite Compilation Flow Finished Successfully!"
puts "================================================================="

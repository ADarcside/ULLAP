# =============================================================================
# de2_115.sdc: Synopsys Design Constraints for Terasic DE2-115 ANC Design
# Target FPGA : Altera/Intel Cyclone IV E EP4CE115F29C7
# =============================================================================

# Primary 50 MHz Master Clock
create_clock -name CLOCK_50 -period 20.000 [get_ports CLOCK_50]

# Audio Codec Bit Clock (WM8731 Master Mode: 64 x fs = 3.125 MHz, period 320.000 ns at 12.5 MHz MCLK)
create_clock -name AUD_BCLK -period 320.000 [get_ports {AUD_BCLK}]

# Clock Domain Crossing: 50 MHz master clock and Audio BCLK are asynchronous
set_clock_groups -asynchronous -group [get_clocks {CLOCK_50}] -group [get_clocks {AUD_BCLK}]

# Automatically derive PLL and clock uncertainties
derive_clock_uncertainty

# Cut timing paths for asynchronous inputs (synchronizers present in RTL)
set_false_path -from [get_ports {KEY[*]}]
set_false_path -from [get_ports {SW[*]}]
set_false_path -from [get_ports {AUD_ADCLRCK}]
set_false_path -from [get_ports {AUD_DACLRCK}]
set_false_path -from [get_ports {AUD_ADCDAT}]

# Cut timing paths for status outputs, audio DAC serial line, and I2C low-speed lines
set_false_path -to [get_ports {LEDR[*]}]
set_false_path -to [get_ports {I2C_SCLK}]
set_false_path -to [get_ports {I2C_SDAT}]
set_false_path -from [get_ports {I2C_SDAT}]
set_false_path -to [get_ports {AUD_XCK}]
set_false_path -to [get_ports {AUD_DACDAT}]


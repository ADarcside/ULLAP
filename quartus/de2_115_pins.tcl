# Terasic DE2-115 Pin Assignments for Cyclone IV E EP4CE115F29C7
# Sourced in Quartus via: source de2_115_pins.tcl

# 50 MHz Master Clocks
set_location_assignment PIN_Y2 -to CLOCK_50
set_instance_assignment -name IO_STANDARD "3.3-V LVTTL" -to CLOCK_50

# Push-button Keys (Active Low)
set_location_assignment PIN_M23 -to KEY[0]
set_location_assignment PIN_M21 -to KEY[1]
set_location_assignment PIN_N21 -to KEY[2]
set_location_assignment PIN_R24 -to KEY[3]
set_instance_assignment -name IO_STANDARD "3.3-V LVTTL" -to KEY[0]
set_instance_assignment -name IO_STANDARD "3.3-V LVTTL" -to KEY[1]
set_instance_assignment -name IO_STANDARD "3.3-V LVTTL" -to KEY[2]
set_instance_assignment -name IO_STANDARD "3.3-V LVTTL" -to KEY[3]

# Slide Switches
set_location_assignment PIN_AB28 -to SW[0]
set_location_assignment PIN_AC28 -to SW[1]
set_location_assignment PIN_AC27 -to SW[2]
set_location_assignment PIN_AD27 -to SW[3]
set_instance_assignment -name IO_STANDARD "3.3-V LVTTL" -to SW[*]

# Red LEDs (Status / Saturation Flags)
set_location_assignment PIN_G19 -to LEDR[0]
set_location_assignment PIN_F19 -to LEDR[1]
set_location_assignment PIN_E19 -to LEDR[2]
set_location_assignment PIN_F21 -to LEDR[3]
set_location_assignment PIN_F18 -to LEDR[4]
set_location_assignment PIN_E18 -to LEDR[5]
set_instance_assignment -name IO_STANDARD "2.5 V" -to LEDR[*]

# Wolfson WM8731 Audio Codec Interface
set_location_assignment PIN_C2 -to AUD_ADCLRCK
set_location_assignment PIN_D2 -to AUD_ADCDAT
set_location_assignment PIN_E3 -to AUD_DACLRCK
set_location_assignment PIN_D1 -to AUD_DACDAT
set_location_assignment PIN_E1 -to AUD_XCK
set_location_assignment PIN_F2 -to AUD_BCLK
set_instance_assignment -name IO_STANDARD "3.3-V LVTTL" -to AUD_*

# I2C Configuration for Codec
set_location_assignment PIN_B7 -to I2C_SCLK
set_location_assignment PIN_A8 -to I2C_SDAT
set_instance_assignment -name IO_STANDARD "3.3-V LVTTL" -to I2C_*

#addition
set_location_assignment PIN_J19 -to LEDR[6]
set_location_assignment PIN_H19 -to LEDR[7]
set_location_assignment PIN_J17 -to LEDR[8]
set_location_assignment PIN_G17 -to LEDR[9]
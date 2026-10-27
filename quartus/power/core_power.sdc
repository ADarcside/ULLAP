# 50 MHz system clock of the DE2-115, as in quartus/de2_115.sdc
create_clock -name clk -period 20.000 [get_ports clk]
derive_clock_uncertainty

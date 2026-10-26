package require ::quartus::stp
# args: instance signal_set trigger csv timeout
lassign $quartus(args) inst ss trg csv tmo
if {$inst eq "cap"} {set ss {signal_set: 2026/10/25 23:25:02  #0}; set trg {trigger: 2026/10/25 23:25:02  #1}} else {set ss {signal_set: 2026/10/25 22:42:52  #2}; set trg {trigger: 2026/10/25 22:42:52  #3}}
open_session -name anc_t9.stp
puts "ARMED $inst"
flush stdout
set rc [catch {run -instance $inst -signal_set $ss -trigger $trg -data_log log1 -timeout $tmo} msg]
puts "RUN rc=$rc $msg"
if {$rc == 0} { export_data_log -instance $inst -signal_set $ss -trigger $trg -data_log log1 -filename $csv -format csv; puts "EXPORTED $csv" }
close_session

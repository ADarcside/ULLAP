#!/bin/sh
# Protocol/corner-case TB for ALGO 0/1/2.   tb/run_protocol.sh [verilator|iverilog]
SIM=${1:-verilator}; HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(dirname "$HERE"); BUILD=${BUILD:-$ROOT/build}; fail=0
mkdir -p "$BUILD"
for L in 8 2; do
  for algo in 0 1 2; do
    d="$BUILD/proto_${algo}_L${L}"; mkdir -p "$d"
    case $SIM in
      verilator) verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_anc_protocol -GALGO=$algo -GL=$L \
                   --Mdir "$d" -o sim "$ROOT/rtl/anc_core.v" "$HERE/tb_anc_protocol.v" > "$d/build.log" 2>&1 && "$d/sim" > "$d/run.log" 2>&1 ;;
      iverilog)  iverilog -g2005 -o "$d/sim.vvp" -s tb_anc_protocol -Ptb_anc_protocol.ALGO=$algo -Ptb_anc_protocol.L=$L \
                   "$ROOT/rtl/anc_core.v" "$HERE/tb_anc_protocol.v" > "$d/build.log" 2>&1 && vvp -n "$d/sim.vvp" > "$d/run.log" 2>&1 ;;
      *) echo "unknown simulator $SIM"; exit 2 ;;
    esac
    line=$(grep 'TB_PROTO' "$d/run.log" 2>/dev/null | tail -1); echo "[proto ALGO=$algo L=$L] ${line:-NO RESULT (see $d/build.log, $d/run.log)}"
    case $line in *"TB_PROTO PASS"*) ;; *) fail=1 ;; esac
  done
done
exit $fail

#!/bin/sh
# Regression runner for tb/tb_anc_core.v. Vendor-neutral: Verilator (>=5, --binary --timing) or Icarus Verilog.
#   tb/run_regression.sh [verilator|iverilog] [name-filter]
# For every line of tb/manifest.txt: build the testbench with the line's parameters, run it, grep TB_RESULT.
# Exit status is 0 only if every selected configuration printed "TB_RESULT PASS".
SIM=${1:-verilator}
FILT=${2:-.}
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(dirname "$HERE")
BUILD=${BUILD:-$ROOT/build}
mkdir -p "$BUILD"; rm -f "$BUILD/summary.txt"; touch "$BUILD/summary.txt"
pass=0; fail=0
grep -v '^#' "$HERE/manifest.txt" | grep -E "$FILT" | while read -r name algo W L MU K ACCW prefix n EPS; do
  EPS=${EPS:-10}
  d="$BUILD/$name"; mkdir -p "$d"
  case $SIM in
    verilator)
      verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_anc_core \
        -GW=$W -GL=$L -GALGO=$algo -GMU_INT=$MU -GK=$K -GACC_W=$ACCW -GEPS_EXP=$EPS \
        --Mdir "$d" -o sim "$ROOT/rtl/anc_core.v" "$HERE/tb_anc_core.v" > "$d/build.log" 2>&1 || { echo "BUILD FAIL $name (see $d/build.log)"; echo "$name BUILDFAIL" >> "$BUILD/summary.txt"; continue; }
      ( cd "$ROOT" && "$d/sim" +vec="$prefix" ) > "$d/run.log" 2>&1 ;;
    iverilog)
      iverilog -g2005 -o "$d/sim.vvp" -s tb_anc_core -Ptb_anc_core.W=$W -Ptb_anc_core.L=$L -Ptb_anc_core.ALGO=$algo \
        -Ptb_anc_core.MU_INT=$MU -Ptb_anc_core.K=$K -Ptb_anc_core.ACC_W=$ACCW -Ptb_anc_core.EPS_EXP=$EPS \
        "$ROOT/rtl/anc_core.v" "$HERE/tb_anc_core.v" > "$d/build.log" 2>&1 || { echo "BUILD FAIL $name"; echo "$name BUILDFAIL" >> "$BUILD/summary.txt"; continue; }
      ( cd "$ROOT" && vvp -n "$d/sim.vvp" +vec="$prefix" ) > "$d/run.log" 2>&1 ;;
    *) echo "unknown simulator $SIM"; exit 2 ;;
  esac
  line=$(grep 'TB_RESULT' "$d/run.log" | tail -1)
  echo "[$name] ${line:-NO TB_RESULT LINE (see $d/run.log)}"
  echo "$name $line" >> "$BUILD/summary.txt"
done
echo "---- summary ----"
total=$(grep -c . "$BUILD/summary.txt" 2>/dev/null); np=$(grep -c 'TB_RESULT PASS' "$BUILD/summary.txt" 2>/dev/null)
echo "passed $np of $total"
[ "$np" = "$total" ] && [ "$total" -gt 0 ]

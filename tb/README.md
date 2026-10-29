# tb

Self-checking testbenches for the core and the board top level. Each one prints a
`TB_RESULT PASS` or `TB_RESULT FAIL` line, which is what the regression runners look for.

| File | What it checks |
|---|---|
| `tb_anc_core.v` | The core against golden vectors, sample by sample: y, e, latency, busy cycles, final weights and saturation flags |
| `tb_anc_core_freeze_hold.v` | The adaptation freeze input under different hold and toggle patterns |
| `tb_anc_protocol.v` | Handshake corner cases: strobes while busy, reset mid-update, back-to-back samples |
| `tb_top.v` | The DE2-115 wrapper with the codec model, tests T1 to T10: I²C start-up and NACK handling, bypass, end-to-end ANC on golden vectors, freeze, reset, saturation LEDs, codec clocks, I²S skew sweep, sample rate and GPIO timing |
| `codec_model.v` | Behavioural WM8731 used by `tb_top.v` |
| `tb_power.v` | Streams vectors at the board rate and dumps a VCD for the power flow |
| `mutants/` | Deliberately broken copies of the wrapper, used to prove the top-level tests catch faults |
| `manifest.txt`, `manifest_hold.txt` | One line per test configuration (ALGO, W, L, MU_INT, K, ACC_W, vector prefix) |
| `anc_sim.mpf` | An early Questa GUI project from the first import; it uses absolute paths from that machine and is kept for reference only |

The usual way to run everything is from the repository root:

```bash
python py/run_iverilog_regression.py    # 86 tests, Icarus Verilog
python py/run_questa_regression.py      # same tests on Questa
```

The shell scripts are a lighter alternative that only cover the core:

```bash
tb/run_regression.sh iverilog            # every line of manifest.txt
tb/run_protocol.sh iverilog              # the protocol testbench
```

New vector sets and manifest lines come from `python py/gen_rtl_vectors.py`. Testbench
parameters must match the vector set, and since `$finish` exit codes differ between
simulators, scripts should always grep the `TB_RESULT` line rather than trust the exit status.

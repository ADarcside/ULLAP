# quartus

The Quartus Prime Lite project for the Terasic DE2-115 (Cyclone IV E EP4CE115F29C7). The core
in `../rtl/` stays vendor neutral; everything board specific is here.

| File | Purpose |
|---|---|
| `anc_de2_115_top.v` | Top level: clocks, reset and switch synchronisers, codec glue, LEDs, GPIO test points |
| `wm8731_i2c_init.v` | Writes the 11 codec registers over I²C at start-up (8.138 kHz, R8 = 0x00C) |
| `i2s_transceiver.v` | I²S receiver and transmitter running from the 50 MHz system clock |
| `build_quartus.tcl` | Scripted build; arguments `ALGO W K EPS_EXP MU_INT` |
| `anc_de2_115.qpf`, `.qsf` | Project and settings (the `.qsf` also carries the Signal Tap assignments) |
| `de2_115_pins.tcl`, `de2_115.sdc` | Pin assignments and timing constraints |
| `anc_t9.stp` | Signal Tap file used for the on-board captures (board test T9) |
| `anc_de2_115.cdf` | Programmer chain file |
| `anc_de2_115.pin`, `.sld` | Pin report and Signal Tap node list written by Quartus, kept as a record of the board build |
| `power/` | Constraints and script for the gate-level power runs on the core alone |
| `BUILD_MANIFEST.md` | Record of one NLMS-Shift build: commit, tool version, parameters, `.sof` checksum |

## Building

```bash
cd quartus
quartus_sh -t build_quartus.tcl 2 12 3 2 512   # NLMS-Shift
quartus_sh -t build_quartus.tcl 1 12 3 0 256   # NLMS
quartus_sh -t build_quartus.tcl 0 12 3 2 256   # LMS
```

Reports land in `output_files/`, which git ignores. The reports behind the paper are archived
in [`../results/quartus_reports/`](../results/quartus_reports/), and
`python py/import_quartus.py` parses new ones into `results/metrics/`.

With `anc_t9.stp` enabled in the `.qsf`, every build includes Signal Tap. The resource and
timing numbers in the paper come from builds without it, so remove the `ENABLE_SIGNALTAP` and
`USE_SIGNALTAP_FILE` lines before a build you want to quote. The gate-level power flow is
described in [`../docs/power_flow.md`](../docs/power_flow.md).

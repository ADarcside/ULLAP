# docs

Notes that explain the design and back up the results.

| Document | What it covers |
|---|---|
| [`design/`](design/) | Architecture, cycle schedule, algorithm derivations and flowcharts |
| [`rtl_interface.md`](rtl_interface.md) | Ports, parameters and handshake of `anc_core` |
| [`wm8731_config.md`](wm8731_config.md) | Codec register settings and clocking, decoded from the RTL |
| [`verification.md`](verification.md) | How the RTL was verified against the Python model, and what was found on the way |
| [`results.md`](results.md) | Walk-through of the simulation study written by the pipeline |
| [`phase1_eps_tuning.md`](phase1_eps_tuning.md) | How the NLMS-Shift step and regulariser were chosen |
| [`board_test.md`](board_test.md) | Bench procedure for the DE2-115, tests T1 to T11 |
| [`power_flow.md`](power_flow.md) | The gate-level power flow and how energy per sample is computed |
| [`related_work.md`](related_work.md) | Notes on prior FPGA noise cancellers and what each one reports |
| [`claims.md`](claims.md) | What the project claims, what it does not, and the evidence for each |
| [`history/`](history/) | Changelogs and test reports from the earlier phases of the project |

`data/` and `figures/` hold copies of a few early tables and plots that older documents link
to. The current versions live in `results/`.

`rtl_regression_log.txt` is the first Verilator regression log (19 configurations, W = 11).
The current regression summaries are in `results/metrics/`.

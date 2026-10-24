# Board builds on commit da0b6f4 (24 Oct 2026)

Built on the authors' PC with `quartus_sh -t build_quartus.tcl <ALGO W K EPS_EXP MU_INT>`,
Quartus Prime Lite 25.1std.0 Build 1129. Full log: `results/local_run_da0b6f4/REPORT.md`.
The `.sof` files are not committed; their SHA-256 is recorded here and in each `sha256.txt`.

| Build | Arguments | .sof SHA-256 |
|---|---|---|
| lms | 0 12 3 2 256 | B9BE384A029679325F3FA358418EE23E6BCD41106EC3100C15E0CEA8DF4672B1 |
| nlms | 1 12 3 0 256 | 3A19777344C961ED1CC7604C710CDE2EAEB55FD2A6EBC969ADC78C2F2BE42527 |
| nlms_shift | 2 12 3 2 512 | 0B223131C80DBDE5BFE16F149EC51EB4E0BA89AD13A7EFFDD5837C2A9F4CEFBC |

Parameters were confirmed in each `map.summary`/map report. Power reports are vectorless
(default 12.5% toggle rate, confidence "low"). The GPIO outputs put I/O bank 4 at 3.3 V
(it was 2.5 V before the test points were added).

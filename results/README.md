# results

Everything the experiments, the tools and the board produced. Most of it is written by
scripts in `py/`; nothing here should need editing by hand.

| Folder or file | Contents |
|---|---|
| `metrics/` | CSV and JSON tables from every study (tuning, sweeps, real audio, statistics, power, regression summaries) |
| `plots/` | Figures 1 to 16 as 300 dpi PNG and vector PDF |
| `paper_numbers.csv` | The headline 20-seed numbers quoted in the paper and the README |
| `board/session1/`, `board/session2/` | Analysis of the Signal Tap captures in `board/`: summaries and per-capture plots |
| `quartus_reports/` | Raw Quartus fit, timing and power reports for the builds the paper quotes, with `.sof` checksums |
| `quartus/` | Template for importing hand-copied Quartus numbers |
| `local_run_da0b6f4/` | Report of the full local run on the authors' PC (Questa, Quartus) at commit da0b6f4 |
| `baseline/` | The frozen phase-0 baseline (`baseline-v0`) the later work was compared against |
| `metadata/` | Configuration and environment of each pipeline run |
| `raw/` | Sample signals saved by the pipeline |
| `logs/` | Archived test, regression, mutation and compile logs from phases 0 to 3 |
| `research_summary.md`, `pipeline_summary.md`, `refinement_report.md` | Written summaries of the simulation study and the refinement tasks |

Each number in these files is either simulated, taken from a Quartus report, or measured on the
board, and the summaries say which. `python py/audit_db_numbers.py` checks that the numbers
quoted in the docs still match these tables.

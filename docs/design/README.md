# design

How ULLAP is built, from the board down to the arithmetic.

| Document | What it covers |
|---|---|
| [`architecture.md`](architecture.md) | The board-level system (WM8731 codec, I²S, I²C start-up) and the core's single-multiplier datapath, delay line, coefficient storage and parameter sizing |
| [`pipeline.md`](pipeline.md) | The cycle schedule of one sample (latency L + 3 for LMS, L + 5 for the NLMS variants) and the stages of the software study |
| [`algorithm.md`](algorithm.md) | LMS, NLMS and NLMS-Shift derived step by step, the stability bounds, why the shift keeps the step between μ/2 and μ, and the Q1.(W−1) fixed-point rules |
| [`flowchart.md`](flowchart.md) | Mermaid flowcharts of start-up, the core state machine, the algorithm branches and saturation handling |

Related code: [`rtl/anc_core.v`](../../rtl/anc_core.v),
[`quartus/anc_de2_115_top.v`](../../quartus/anc_de2_115_top.v),
[`py/fixedpoint.py`](../../py/fixedpoint.py) and [`py/algos.py`](../../py/algos.py).
Results: [`results/research_summary.md`](../../results/research_summary.md) and
[`results/plots/`](../../results/plots/).

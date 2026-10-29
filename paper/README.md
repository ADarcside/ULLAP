# paper

The journal manuscript. Two front ends share one body so the text only has to be edited once:

| File | Role |
|---|---|
| `body.tex` | The paper itself: all sections, equations, TikZ block diagrams, tables and figures |
| `abstract.tex` | Shared abstract |
| `refs.bib` | Shared bibliography |
| `ullap_manuscript.tex` → `.pdf` | Elsevier `elsarticle` version |
| `ullap_ieee.tex` → `.pdf` | IEEE `IEEEtran` version |
| `tab_*.tex` | Tables generated from `results/metrics/` by `make_tables.py` |
| `make_fig_convergence.py`, `fig1_convergence_paper.*` | The convergence figure in the paper's own size |

The other figures are read straight from `../results/plots/`.

## Building

```bash
cd paper
python make_tables.py
latexmk -pdf ullap_manuscript.tex ullap_ieee.tex
```

On Debian or Ubuntu the needed TeX packages are `texlive-latex-extra`, `texlive-publishers`,
`texlive-science` and `texlive-pictures`.

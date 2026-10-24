"""Generate LaTeX tables for the manuscript from committed result CSVs.

    python paper/make_tables.py   ->  paper/tab_real_audio.tex, paper/tab_paired.tex
"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, "results", "metrics")
NOISE = {"air_conditioner": "Air conditioner", "vacuum": "Vacuum cleaner",
         "copy_machine": "Copy machine", "babble": "Babble"}
ALG = {"lms": "LMS", "nlms": "NLMS", "nlms_shift": "NLMS-Shift"}
SCEN = {"stationary": "Stationary", "amp_steps": "Amplitude steps", "path_switch": "Path switch", "wav": "Recorded chord"}


def real_audio(crosstalk):
    rows = [r for r in csv.DictReader(open(os.path.join(M, "real_audio_summary.csv")))
            if r["kind"] == "fixed" and r["crosstalk"] == crosstalk]
    out = ["\\begin{tabular}{llccc}\\toprule",
           "Noise & Metric & LMS & NLMS & NLMS-Shift\\\\\\midrule"]
    for nz, label in NOISE.items():
        sub = {r["algo"]: r for r in rows if r["noise"] == nz}
        ref = sub["lms"]
        out.append(f"\\multirow{{3}}{{*}}{{{label}}} & NR (dB) & " +
                   " & ".join(f"{float(sub[a]['nr']):.2f} $\\pm$ {float(sub[a]['nr_ci95']):.2f}" for a in ALG) + "\\\\")
        out.append(f" & STOI (input {float(ref['stoi_in']):.3f}) & " +
                   " & ".join(f"{float(sub[a]['stoi']):.3f}" for a in ALG) + "\\\\")
        out.append(f" & PESQ (input {float(ref['pesq_in']):.2f}) & " +
                   " & ".join(f"{float(sub[a]['pesq']):.2f}" for a in ALG) + "\\\\\\addlinespace")
    out[-1] = out[-1].replace("\\addlinespace", "")
    out.append("\\bottomrule\\end{tabular}")
    return "\n".join(out)


def paired():
    rows = list(csv.DictReader(open(os.path.join(M, "paired_stats.csv"))))
    out = ["\\begin{tabular}{llcccc}\\toprule",
           "Scenario & Pair & Mean diff. (dB) & 95\\% CI & $p$ (paired $t$) & TOST $\\pm$0.5 dB\\\\\\midrule"]
    for r in rows:
        out.append(f"{SCEN[r['scenario']]} & {ALG[r['a']]} $-$ {ALG[r['b']]} & {float(r['mean_diff']):+.2f} & "
                   f"[{float(r['ci95_low']):+.2f}, {float(r['ci95_high']):+.2f}] & {float(r['p_ttest']):.2g} & "
                   f"{'equivalent' if r['equivalent'] == 'True' else 'not equiv.'}\\\\")
    out.append("\\bottomrule\\end{tabular}")
    return "\n".join(out)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(M, "real_audio_summary.csv")):
        open(os.path.join(here, "tab_real_audio.tex"), "w").write(real_audio("none") + "\n")
        open(os.path.join(here, "tab_real_audio_xt.tex"), "w").write(real_audio("-20dB") + "\n")
    if os.path.exists(os.path.join(M, "paired_stats.csv")):
        open(os.path.join(here, "tab_paired.tex"), "w").write(paired() + "\n")
    print("tables written")


if __name__ == "__main__":
    main()

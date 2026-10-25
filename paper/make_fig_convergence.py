"""Manuscript version of Fig. 1: running NR for the four scenarios described in the paper.

The report's results/plots/fig1_convergence also shows the 'feedback' scenario, which applies a
recirculating delay to d[n] only (no closed loop through the canceller) and is not described in the
paper, so it is left out here.   python paper/make_fig_convergence.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "py"))
from experiment_config import FAIR_TUNED_SETTINGS as F  # noqa: E402
from fixedpoint import FxCfg, run_fixed  # noqa: E402
from metrics import FS, curves  # noqa: E402
from signals import make_scenario  # noqa: E402
from visualize import plot_fig1_convergence  # noqa: E402

WAV = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
sc_curves, sc_events = {}, {}
for name in ("stationary", "amp_steps", "path_switch", "wav"):
    sc = make_scenario(name, 16000, 1, WAV if name == "wav" else None)
    sc_events[name] = [ev / FS for ev in sc.events]
    sc_curves[name] = {}
    for al in ("lms", "nlms", "nlms_shift"):
        r = run_fixed(al, sc.x, sc.d, 32, F[al]["mu"], FxCfg(W=12, eps_exp=F[al]["eps_exp"]))
        sc_curves[name][al] = curves(sc, r["e"], r["W"], 32)
plot_fig1_convergence(sc_curves, sc_events, os.path.join(ROOT, "paper", "fig1_convergence_paper"), fs=FS)

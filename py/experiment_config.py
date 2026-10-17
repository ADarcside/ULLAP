"""Unified Experiment Configuration and Reproducibility Metadata Manager.

Provides structured, configurable parameters for ANC experiments:
  - Algorithm configurations (LMS, NLMS, NLMS-shift)
  - Scenarios (stationary, amp_steps, path_switch, wav)
  - Signal parameters (sampling rate, duration, filter length)
  - Fixed-point word-length sweeps (8 to 24 bits)
  - Candidate selection thresholds
  - Reproducible seed definitions
  - Automatic export of timestamped run metadata to results/metadata/
"""
from dataclasses import dataclass, field, asdict
import json
import os
import time
from typing import List, Dict, Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class ExperimentConfig:
    experiment_id: str = field(default_factory=lambda: f"anc_exp_{time.strftime('%Y%m%d_%H%M%S')}")
    algorithms: List[str] = field(default_factory=lambda: ["lms", "nlms", "nlms_shift"])
    scenarios: List[str] = field(default_factory=lambda: ["stationary", "amp_steps", "path_switch", "wav"])
    sample_rate: int = 8000
    sample_count: int = 16000
    filter_length: int = 32
    tune_seed: int = 100
    eval_seeds: List[int] = field(default_factory=lambda: [1, 2, 3])
    bit_widths: List[int] = field(default_factory=lambda: list(range(8, 25)))
    eps_exp: int = 2
    thresholds: Dict[str, float] = field(default_factory=lambda: {
        "mean_deg": 1.0,
        "max_deg": 3.0,
        "ovf_rate": 1e-3,
        "min_nr": 10.0
    })
    wav_path: str = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
    target_fpga: str = "Terasic DE2-115 (Altera Cyclone IV E EP4CE115F29C7)"
    results_root: str = os.path.join(ROOT, "results")
    quick_mode: bool = False
    jobs: int = 1

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        return d

    def save_metadata(self, filename: str = None) -> str:
        """Serialize configuration and environment metadata to JSON."""
        out_dir = os.path.join(self.results_root, "metadata")
        os.makedirs(out_dir, exist_ok=True)
        fname = filename or f"{self.experiment_id}_metadata.json"
        out_path = os.path.join(out_dir, fname)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return out_path

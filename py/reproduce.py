#!/usr/bin/env python3
"""Unified Reproducibility Driver for all Refinement Experiments.

Usage:
  python py/reproduce.py                  # runs all tasks (1, 2, 3, 5, 7)
  python py/reproduce.py --task 1         # runs task 1 (amp_steps reproducibility)
  python py/reproduce.py --task 2         # runs task 2 (fixed-point sweep)
  python py/reproduce.py --task 3         # runs task 3 (gate A hybrid)
  python py/reproduce.py --task 5         # runs task 5 (level robustness)
  python py/reproduce.py --task 7         # runs task 7 (acoustic feedback)
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "py"))

import exp_reproduce_task1
import exp_sweep_task2
import exp_hybrid_task3
import exp_level_robustness
import exp_feedback_task7

def main():
    parser = argparse.ArgumentParser(description="Unified Refinement Reproduction Suite")
    parser.add_argument("--task", choices=["1", "2", "3", "5", "7", "all"], default="all",
                        help="Select specific task to run (default: all)")
    args = parser.parse_args()

    t = args.task
    if t in ("1", "all"):
        exp_reproduce_task1.run_task1()
    if t in ("2", "all"):
        exp_sweep_task2.run_task2()
    if t in ("3", "all"):
        exp_hybrid_task3.run_task3()
    if t in ("5", "all"):
        exp_level_robustness.run_level_robustness()
    if t in ("7", "all"):
        exp_feedback_task7.run_feedback()

if __name__ == "__main__":
    main()

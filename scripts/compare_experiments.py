#!/usr/bin/env python3
"""Run all experiments; optional flags support a quick pipeline smoke test."""
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pigeon_ai.comparison import run_comparison
from pigeon_ai.experiments import EXPERIMENTS
from pigeon_ai.model import MODEL_DIR

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--versions", nargs="+", choices=list(EXPERIMENTS))
    parser.add_argument("--out-dir", type=Path, default=MODEL_DIR / "experiments")
    parser.add_argument("--no-shap", action="store_true")
    parser.add_argument("--no-stability", action="store_true")
    args = parser.parse_args()
    print(run_comparison(args.versions, args.out_dir, not args.no_shap, not args.no_stability))

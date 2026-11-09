#!/usr/bin/env python3
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pigeon_ai.good_areas import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Experiment: train on well-served areas only and compare with the production model.")
    parser.add_argument("--seed", type=int, default=0, help="forest seed for the good-areas model")
    args = parser.parse_args()
    print(run(seed=args.seed))

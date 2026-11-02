#!/usr/bin/env python3
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pigeon_ai.model import THRESHOLD, TARGETS, run

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train and evaluate the placement model.")
    parser.add_argument("--target", default="toilets", choices=list(TARGETS))
    parser.add_argument("--features", default="latest", help="feature set name, e.g. latest or v1")
    parser.add_argument("--threshold", type=float, default=THRESHOLD,
                        help="how many more toilets than exist the prediction must be to flag a candidate")
    args = parser.parse_args()
    if args.features not in TARGETS[args.target].feature_sets:
        parser.error(f"--features must be one of {list(TARGETS[args.target].feature_sets)}")
    print(run(args.target, args.features, args.threshold))

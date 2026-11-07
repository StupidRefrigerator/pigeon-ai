#!/usr/bin/env python3
"""Save full-data V1/V5/V6 models for the local comparison app (no CV reruns)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pigeon_ai.prototype import train_final_models

if __name__ == "__main__":
    train_final_models()

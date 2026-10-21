"""Stable repository paths and artifact digests; no ML imports."""
import hashlib
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[4]
SOURCE = BACKEND / "data/c2/microclimate/synthetic/c1_synthetic_hourly_2025_2nodes.csv"
OUTPUT = BACKEND / "experiments/c2/microclimate/phase1"
SCALED_OUTPUT = BACKEND / "experiments/c2/microclimate/phase1_masked_scaled"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()



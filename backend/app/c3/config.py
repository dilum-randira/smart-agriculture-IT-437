"""Settings for C3 that the whole package shares.

Only structural settings live here for now. Agronomic numbers (crop
coefficients, soil properties, water price ...) are added in later stages,
each one with a comment saying where the value came from.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Folder locations
# ---------------------------------------------------------------------------
# This file is backend/app/c3/config.py, so parents[2] is the backend/ folder.
BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "c3_data"

RAW_DATA_DIR = DATA_DIR / "raw"              # files exactly as downloaded / received
PROCESSED_DATA_DIR = DATA_DIR / "processed"  # cleaned files ready for C3
SAMPLE_DATA_DIR = DATA_DIR / "sample"        # small made-up files for development only
OUTPUT_DIR = DATA_DIR / "outputs"            # schedules, charts, experiment results

ALL_DATA_FOLDERS = [RAW_DATA_DIR, PROCESSED_DATA_DIR, SAMPLE_DATA_DIR, OUTPUT_DIR]

# ---------------------------------------------------------------------------
# Scheduling settings
# ---------------------------------------------------------------------------
SCHEDULE_DAYS = 7  # the irrigation plan always covers the next 7 days

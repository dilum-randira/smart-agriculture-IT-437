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

# ---------------------------------------------------------------------------
# Crop: Nai Miris (Capsicum chinense, Sri Lankan "Scotch bonnet" type)
# ---------------------------------------------------------------------------
# PROXY: FAO-56 bell pepper, no Nai Miris data.
# FAO-56 (Allen et al., 1998) has no row for Nai Miris. Every value below is
# copied from the "Sweet peppers (bell)" row (Capsicum annuum, a different
# species). Replace each one when a Sri Lankan / Nai Miris source is found.
# This limitation must be stated in the thesis.
CROP_NAME = "Nai Miris (Capsicum chinense)"

# PROXY: FAO-56 bell pepper, no Nai Miris data. FAO-56 Table 12.
KC_MID = 1.05   # dimensionless, mid-season crop coefficient
KC_END = 0.90   # dimensionless, end-of-season crop coefficient
# KC_INI is not set yet: the online FAO-56 Table 12 shows it only as an
# image, so the value has not been checked. Fill it in from the printed table.
KC_INI = None

# PROXY: FAO-56 bell pepper, no Nai Miris data. FAO-56 Table 22.
ROOT_DEPTH_MIN_M = 0.5   # m, smallest maximum effective rooting depth
ROOT_DEPTH_MAX_M = 1.0   # m, largest maximum effective rooting depth
DEPLETION_FRACTION_P = 0.30  # dimensionless, soil water depletion for no stress

# Crop stage lengths (FAO-56 Table 11) are not set yet: the bell pepper rows
# are for Europe/Mediterranean (125 days) and an arid region (210 days),
# neither of which fits Sri Lanka. A local source is needed.

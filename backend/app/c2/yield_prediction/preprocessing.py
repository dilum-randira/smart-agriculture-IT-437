
from pathlib import Path
import pandas as pd

# Resolve paths relative to this script
BACKEND = Path(__file__).resolve().parents[3]

RAW_FILE = (
    BACKEND / "data/c2/yield/raw"
    / "PeerJ_360_genotype_year_records.csv"
)

OUTPUT_FILE = (
    BACKEND / "data/c2/yield/processed"
    / "peerj_yield_cleaned.csv"
)

TARGET = "fruit_yield_g_per_plant"

FEATURES = [
    "plant_height_cm",
    "main_branches",
    "leaf_length_cm",
    "leaf_breadth_cm",
    "days_to_50pct_flowering",
]


def preprocess():
    print("Loading original yield dataset...")

    df = pd.read_csv(RAW_FILE)

    print("Original rows:", len(df))
    print("Original columns:", len(df.columns))

    # 1. Required-column validation
    required = [
        "genotype_id",
        "study_year_index",
        "species",
        "observation_unit",
        "fruit_yield_weight_basis",
        TARGET,
        *FEATURES,
    ]

    missing_columns = [
        col for col in required if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    # 2. Check genotype-year duplicates
    duplicates = df.duplicated(
        subset=["genotype_id", "study_year_index"]
    ).sum()

    print("Duplicate genotype-year records:", duplicates)

    if duplicates:
        raise ValueError("Duplicate genotype-year records found")

    # 3. Validate source and observation type
    if not df["species"].eq("Capsicum chinense").all():
        raise ValueError("Unexpected crop species")

    if not df["observation_unit"].eq(
        "genotype_year_trait_aggregate"
    ).all():
        raise ValueError("Unexpected observation unit")

    # 4. Convert numerical columns
    for col in FEATURES + [TARGET]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print("\nMissing values:")
    print(df[FEATURES + [TARGET]].isna().sum())

    # 5. Remove records without an observed target
    before = len(df)
    df = df.dropna(subset=[TARGET]).copy()

    print("Rows without target removed:", before - len(df))

    # 6. Reject impossible negative yield
    if (df[TARGET] < 0).any():
        raise ValueError("Negative yield values detected")

    # Preserve source metadata and original observations.
    # Do not impute feature values before train/test splitting.
    df = df.sort_values(
        ["genotype_id", "study_year_index"]
    ).reset_index(drop=True)

    OUTPUT_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    df.to_csv(OUTPUT_FILE, index=False)

    print("\nPreprocessing completed!")
    print("Final rows:", len(df))
    print("Unique genotypes:", df["genotype_id"].nunique())
    print("Yield basis:", df["fruit_yield_weight_basis"].unique())
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    preprocess()

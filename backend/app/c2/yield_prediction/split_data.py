
from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupKFold, GroupShuffleSplit


BACKEND = Path(__file__).resolve().parents[3]

INPUT_FILE = (
    BACKEND / "data/c2/yield/processed"
    / "peerj_yield_cleaned.csv"
)

OUTPUT_DIR = BACKEND / "data/c2/yield/processed"

GROUP_COLUMN = "genotype_id"
RANDOM_STATE = 42
N_FOLDS = 5


def prepare_splits():
    # 1. Load preprocessed data
    df = pd.read_csv(INPUT_FILE)

    print("Total records:", len(df))
    print("Unique genotypes:", df[GROUP_COLUMN].nunique())

    # 2. Reserve 15% of genotypes for final testing
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.15,
        random_state=RANDOM_STATE,
    )

    development_idx, test_idx = next(
        splitter.split(df, groups=df[GROUP_COLUMN])
    )

    development = df.iloc[development_idx].copy()
    test = df.iloc[test_idx].copy()

    # 3. Confirm no genotype overlap
    dev_groups = set(development[GROUP_COLUMN])
    test_groups = set(test[GROUP_COLUMN])

    assert dev_groups.isdisjoint(test_groups), (
        "Data leakage: genotype overlap detected"
    )

    # 4. Generate 5 grouped CV folds
    cv = GroupKFold(n_splits=N_FOLDS)

    fold_assignments = pd.Series(
        index=development.index,
        dtype="int64",
    )

    for fold_number, (train_idx, val_idx) in enumerate(
        cv.split(
            development,
            groups=development[GROUP_COLUMN],
        ),
        start=1,
    ):
        train_groups = set(
            development.iloc[train_idx][GROUP_COLUMN]
        )
        val_groups = set(
            development.iloc[val_idx][GROUP_COLUMN]
        )

        assert train_groups.isdisjoint(val_groups)

        fold_assignments.loc[
            development.iloc[val_idx].index
        ] = fold_number

        print(
            f"Fold {fold_number}: "
            f"{len(train_idx)} training rows, "
            f"{len(val_idx)} validation rows"
        )

    development["cv_fold"] = fold_assignments.astype(int)
    test["cv_fold"] = -1

    # 5. Verify each genotype belongs to one CV fold
    if (
        development.groupby(GROUP_COLUMN)["cv_fold"]
        .nunique()
        .max()
        != 1
    ):
        raise ValueError("Genotype assigned to multiple folds")

    # 6. Save reproducible splits
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    development.to_csv(
        OUTPUT_DIR / "peerj_development.csv",
        index=False,
    )

    test.to_csv(
        OUTPUT_DIR / "peerj_test.csv",
        index=False,
    )

    print("\nDevelopment rows:", len(development))
    print("Test rows:", len(test))
    print("Development genotypes:", len(dev_groups))
    print("Test genotypes:", len(test_groups))
    print("Genotype overlap: NONE")
    print("CV folds:", N_FOLDS)
    print("Split preparation completed!")


if __name__ == "__main__":
    prepare_splits()

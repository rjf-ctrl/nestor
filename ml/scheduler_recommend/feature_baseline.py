#!/usr/bin/env python3

import sys
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import GroupShuffleSplit


def evaluate_feature(X, y, groups):

    gss = GroupShuffleSplit(
        n_splits=1,
        test_size=0.2,
        random_state=42,
    )

    train_idx, test_idx = next(gss.split(X, y, groups))

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]

    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    pred = model.predict(X_test)

    return accuracy_score(y_test, pred)


def main():

    if len(sys.argv) != 2:
        print("Usage: python feature_baseline.py dataset.csv")
        sys.exit(1)

    df = pd.read_csv(sys.argv[1])

    groups = df["experiment_id"]

    y = df["best_scheduler"]

    feature_cols = [
        c for c in df.columns
        if c not in ("experiment_id", "best_scheduler")
    ]

    print("=" * 70)
    print("FEATURE BASELINE ANALYSIS")
    print("=" * 70)

    results = []

    # ------------------------------------------------------
    # Individual Features
    # ------------------------------------------------------

    for feature in feature_cols:

        X = df[[feature]]

        acc = evaluate_feature(X, y, groups)

        results.append((feature, acc))

    # ------------------------------------------------------
    # All Features
    # ------------------------------------------------------

    X_all = df[feature_cols]

    full_acc = evaluate_feature(X_all, y, groups)

    # ------------------------------------------------------
    # Results
    # ------------------------------------------------------

    results.sort(key=lambda x: x[1], reverse=True)

    print("\nIndividual Feature Accuracy")
    print("-" * 70)

    for feature, acc in results:
        print(f"{feature:30s} {acc:.4f}")

    print("\n" + "=" * 70)
    print(f"All Features Accuracy : {full_acc:.4f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
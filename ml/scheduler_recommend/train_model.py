#!/usr/bin/env python3

import os
import sys
import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)


def main():
    if len(sys.argv) != 2:
        print("Usage: python train_model.py <dataset.csv>")
        sys.exit(1)

    dataset_path = sys.argv[1]

    print("=" * 60)
    print("Loading Dataset")
    print("=" * 60)

    df = pd.read_csv(dataset_path)

    if "best_scheduler" not in df.columns:
        print("Error: best_scheduler column not found.")
        sys.exit(1)

    if "experiment_id" not in df.columns:
        print("Error: experiment_id column not found.")
        sys.exit(1)

    # ----------------------------------------------------
    # Features, labels and experiment groups
    # ----------------------------------------------------

    groups = df["experiment_id"]

    X = df.drop(columns=["experiment_id", "best_scheduler"])
    y = df["best_scheduler"]

    feature_names = X.columns

    print(f"Samples    : {len(df)}")
    print(f"Features   : {len(feature_names)}")
    print(f"Experiments: {groups.nunique()}")

    # ----------------------------------------------------
    # Group-aware Train/Test Split
    # ----------------------------------------------------

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

    print(f"\nTraining Samples : {len(X_train)}")
    print(f"Testing Samples  : {len(X_test)}")

    train_groups = set(groups.iloc[train_idx])
    test_groups = set(groups.iloc[test_idx])

    print(f"Training Experiments : {len(train_groups)}")
    print(f"Testing Experiments  : {len(test_groups)}")
    print(f"Experiment Overlap   : {len(train_groups & test_groups)}")

    # ----------------------------------------------------
    # Train Model
    # ----------------------------------------------------

    print("\nTraining Random Forest...")

    model = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    print("Training complete.")

    # ----------------------------------------------------
    # Evaluate
    # ----------------------------------------------------

    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)

    print("\n" + "=" * 60)
    print("MODEL EVALUATION")
    print("=" * 60)

    print(f"\nAccuracy: {accuracy:.4f}")

    print("\nClassification Report")
    print("-" * 60)
    print(classification_report(y_test, y_pred))

    print("Confusion Matrix")
    print("-" * 60)
    print(confusion_matrix(y_test, y_pred))

    # ----------------------------------------------------
    # Feature Importance
    # ----------------------------------------------------

    print("\nFeature Importance")
    print("-" * 60)

    importance = pd.DataFrame({
        "Feature": feature_names,
        "Importance": model.feature_importances_,
    })

    importance = importance.sort_values(
        by="Importance",
        ascending=False,
    )

    print(importance.to_string(index=False))

    # ----------------------------------------------------
    # Save Model
    # ----------------------------------------------------

    os.makedirs("models", exist_ok=True)

    model_path = "models/random_forest.pkl"

    joblib.dump(model, model_path)

    print(f"\nModel saved to: {model_path}")


if __name__ == "__main__":
    main()
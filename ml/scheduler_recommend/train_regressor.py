#!/usr/bin/env python3

import os
import sys
import joblib
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)


def main():

    if len(sys.argv) != 2:
        print("Usage: python train_regressor.py <regression_dataset.csv>")
        sys.exit(1)

    dataset_path = sys.argv[1]

    print("=" * 60)
    print("Loading Regression Dataset")
    print("=" * 60)

    df = pd.read_csv(dataset_path)

    groups = df["experiment_id"]

    feature_names = [
        c for c in df.columns
        if c not in [
            "experiment_id",
            "throughput_mb",
            "fio_latency_us",
        ]
    ]

    X = df[feature_names]
    y = df["throughput_mb"]

    print(f"Samples     : {len(df)}")
    print(f"Features    : {len(feature_names)}")
    print(f"Experiments : {groups.nunique()}")

    ###########################################################
    # Group-aware split
    ###########################################################

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.2,
        random_state=42,
    )

    train_idx, test_idx = next(
        splitter.split(
            X,
            y,
            groups,
        )
    )

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]

    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    print()
    print(f"Training Samples : {len(X_train)}")
    print(f"Testing Samples  : {len(X_test)}")

    train_groups = set(groups.iloc[train_idx])
    test_groups = set(groups.iloc[test_idx])

    print(f"Training Experiments : {len(train_groups)}")
    print(f"Testing Experiments  : {len(test_groups)}")
    print(f"Experiment Overlap   : {len(train_groups & test_groups)}")

    ###########################################################
    # Train
    ###########################################################

    print("\nTraining Random Forest Regressor...")

    model = RandomForestRegressor(
        n_estimators=300,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train,
        y_train,
    )

    print("Training complete.")

    ###########################################################
    # Predict
    ###########################################################

    y_pred = model.predict(X_test)

    ###########################################################
    # Metrics
    ###########################################################

    mae = mean_absolute_error(
        y_test,
        y_pred,
    )

    mse = mean_squared_error(
        y_test,
        y_pred,
    )

    rmse = mse ** 0.5

    r2 = r2_score(
        y_test,
        y_pred,
    )

    print()
    print("=" * 60)
    print("MODEL EVALUATION")
    print("=" * 60)

    print(f"\nMAE  : {mae:.2f} MB/s")
    print(f"RMSE : {rmse:.2f} MB/s")
    print(f"R²   : {r2:.4f}")

    ###########################################################
    # Feature importance
    ###########################################################

    importance = pd.DataFrame({
        "Feature": feature_names,
        "Importance": model.feature_importances_,
    })

    importance = importance.sort_values(
        by="Importance",
        ascending=False,
    )

    print("\nFeature Importance")
    print("-" * 60)
    print(importance.to_string(index=False))

    ###########################################################
    # Save
    ###########################################################

    os.makedirs(
        "models",
        exist_ok=True,
    )

    model_path = "models/random_forest_regressor.pkl"

    joblib.dump(
        model,
        model_path,
    )

    print()
    print(f"Model saved to: {model_path}")


if __name__ == "__main__":
    main()
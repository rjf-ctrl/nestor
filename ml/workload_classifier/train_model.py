#!/usr/bin/env python3

import argparse
import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)

    X = df.drop(columns=["workload_class"])

    y = df["workload_class"]

    encoder = LabelEncoder()
    y = encoder.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    pred = model.predict(X_test)

    print()
    print(f"Test Accuracy : {accuracy_score(y_test, pred):.4f}")
    print()
    print(classification_report(
        y_test,
        pred,
        target_names=encoder.classes_
    ))

    train_pred = model.predict(X_train)

    print(f"Train Accuracy: {accuracy_score(y_train, train_pred):.4f}")

    cm = confusion_matrix(y_test, pred)

    print("Confusion Matrix:")
    print(cm)

    cm_df = pd.DataFrame(
        cm,
        index=encoder.classes_,
        columns=encoder.classes_,
    )

    import os
    os.makedirs("models", exist_ok=True)

    cm_df.to_csv("models/confusion_matrix.csv")
    joblib.dump(model, "models/random_forest.pkl")
    joblib.dump(encoder, "models/label_encoder.pkl")
    joblib.dump(list(X.columns), "models/feature_names.pkl")

    print()
    print("Model saved.")


if __name__ == "__main__":
    main()
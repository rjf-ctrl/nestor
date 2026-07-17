#!/usr/bin/env python3

"""
Nestor Workload Predictor

Provides a simple API for predicting workload classes from
telemetry feature vectors.

Used by:
    - CLI
    - predict.py
    - Future dashboard/API
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd


class WorkloadPredictor:

    def __init__(self):
        model_dir = Path(__file__).parent / "models"

        self.model = joblib.load(model_dir / "random_forest.pkl")
        self.encoder = joblib.load(model_dir / "label_encoder.pkl")
        self.feature_names = joblib.load(model_dir / "feature_names.pkl")

    def predict(self, df: pd.DataFrame):
        """
        Predict workload from one or more telemetry windows.

        Parameters
        ----------
        df : pandas.DataFrame
            Telemetry feature dataframe.

        Returns
        -------
        dict
            {
                "workload": str,
                "confidence": float,
                "probabilities": dict,
                "window_predictions": list
            }
        """

        # --------------------------------------------------
        # Validate features
        # --------------------------------------------------

        missing = set(self.feature_names) - set(df.columns)

        if missing:
            raise ValueError(
                f"Missing required features: {sorted(missing)}"
            )

        # Ensure correct feature order
        df = df[self.feature_names]

        # --------------------------------------------------
        # Predict every window
        # --------------------------------------------------

        probabilities = self.model.predict_proba(df)

        window_ids = np.argmax(probabilities, axis=1)
        window_labels = self.encoder.inverse_transform(window_ids)

        window_predictions = []

        for i in range(len(df)):
            window_predictions.append(
                {
                    "window": i + 1,
                    "workload": window_labels[i],
                    "confidence": float(probabilities[i].max()),
                }
            )

        # --------------------------------------------------
        # Overall prediction
        # --------------------------------------------------

        average_probabilities = probabilities.mean(axis=0)

        best_index = int(np.argmax(average_probabilities))

        overall_workload = self.encoder.inverse_transform(
            [best_index]
        )[0]

        overall_confidence = float(
            average_probabilities[best_index]
        )

        probability_table = {
            cls: float(prob)
            for cls, prob in zip(
                self.encoder.classes_,
                average_probabilities,
            )
        }

        return {
            "workload": overall_workload,
            "confidence": overall_confidence,
            "probabilities": probability_table,
            "window_predictions": window_predictions,
        }

    def predict_file(self, csv_path):
        """
        Predict workload directly from a CSV file.
        """

        df = pd.read_csv(csv_path)
        return self.predict(df)
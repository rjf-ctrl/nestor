#!/usr/bin/env python3

import joblib
import pandas as pd
import numpy as np

from hueristics import SchedulerAdvisor

# --------------------------------------------------
# Load model
# --------------------------------------------------

model = joblib.load("models/random_forest.pkl")
encoder = joblib.load("models/label_encoder.pkl")
feature_names = joblib.load("models/feature_names.pkl")

advisor = SchedulerAdvisor("scheduler_heuristics.json")

# --------------------------------------------------
# Load sample
# --------------------------------------------------

sample = pd.read_csv("sample.csv")
sample = sample[feature_names]

# --------------------------------------------------
# Predict every window
# --------------------------------------------------

probabilities = model.predict_proba(sample)

predictions = encoder.inverse_transform(
    np.argmax(probabilities, axis=1)
)

print("=" * 60)
print("Per-window Predictions")
print("=" * 60)

for i in range(len(sample)):

    pred = predictions[i]
    conf = probabilities[i].max() * 100

    print(f"Window {i+1:2d}")
    print(f"  Workload   : {pred}")
    print(f"  Confidence : {conf:.2f}%")
    print()

# --------------------------------------------------
# Average probabilities across ALL windows
# --------------------------------------------------

avg_probs = probabilities.mean(axis=0)

best_idx = np.argmax(avg_probs)

overall_workload = encoder.inverse_transform([best_idx])[0]

overall_confidence = avg_probs[best_idx] * 100

# --------------------------------------------------
# Print overall workload
# --------------------------------------------------

print("=" * 60)
print("Overall Workload")
print("=" * 60)

print(f"Detected workload : {overall_workload}")
print(f"Confidence        : {overall_confidence:.2f}%")

print("\nClass Probabilities\n")

sorted_idx = np.argsort(avg_probs)[::-1]

for idx in sorted_idx:

    workload = encoder.inverse_transform([idx])[0]
    prob = avg_probs[idx] * 100

    print(f"{workload:<20} {prob:6.2f}%")

# --------------------------------------------------
# Scheduler recommendations
# --------------------------------------------------

print()
advisor.recommend(overall_workload)
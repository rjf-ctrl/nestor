#!/usr/bin/env python3

import os
import joblib
import shap
import pandas as pd
import matplotlib.pyplot as plt

os.makedirs("plots", exist_ok=True)

model = joblib.load("models/random_forest.pkl")

df = pd.read_csv("datasets/cleaned_dataset.csv")
X = df.drop(columns=["workload_class"])

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)

shap.summary_plot(
    shap_values,
    X,
    plot_type="dot",
    show=False,
)

plt.tight_layout()
plt.savefig("plots/shap_summary.png", dpi=300)
plt.close()

print("SHAP summary saved to plots/shap_summary.png")
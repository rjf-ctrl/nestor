import joblib
import pandas as pd
import matplotlib.pyplot as plt
import os

os.makedirs("plots", exist_ok=True)

model = joblib.load("models/random_forest.pkl")

df = pd.read_csv("datasets/cleaned_dataset.csv")

X = df.drop(columns=["workload_class"])

importance = pd.Series(
    model.feature_importances_,
    index=X.columns
)

importance = importance.sort_values()

plt.figure(figsize=(8,6))

importance.plot(kind="barh")

plt.tight_layout()

plt.savefig("plots/feature_importance.png")

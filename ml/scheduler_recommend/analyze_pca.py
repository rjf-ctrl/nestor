#!/usr/bin/env python3

import sys
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

if len(sys.argv) != 2:
    print("Usage: python analyze_pca.py dataset.csv")
    sys.exit(1)

df = pd.read_csv(sys.argv[1])

X = df.drop(columns=["experiment_id", "best_scheduler"])
y = df["best_scheduler"]

X = StandardScaler().fit_transform(X)

pca = PCA(n_components=2)
X_pca = pca.fit_transform(X)

plt.figure(figsize=(8,6))

for label in sorted(y.unique()):
    idx = y == label
    plt.scatter(
        X_pca[idx,0],
        X_pca[idx,1],
        s=10,
        alpha=0.5,
        label=label
    )

plt.xlabel(f"PC1 ({100*pca.explained_variance_ratio_[0]:.1f}%)")
plt.ylabel(f"PC2 ({100*pca.explained_variance_ratio_[1]:.1f}%)")
plt.title("PCA of Nestor Dataset")
plt.legend()
plt.tight_layout()

plt.savefig("pca_plot.png", dpi=300)
print("Saved PCA plot to pca_plot.png")
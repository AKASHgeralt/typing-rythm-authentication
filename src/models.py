"""Nearest-neighbour distance scorer (the KNN model of this project).

With only 5 impostor attempts per account, a normal KNN classifier sees almost
only the owner's attempts among the neighbours, so it scores impostors as
genuine too. This scorer therefore learns ONLY from the owner's attempts:

  1. d = mean Euclidean distance from the new attempt to its k nearest
     owner attempts (features standardised first).
  2. d is divided by the typical distance between the owner's own attempts
     (median over the owner's attempts of the same k-neighbour distance),
     so d_norm = 1 means "as close as the owner's attempts usually are".
  3. genuine score = 1 / (1 + d_norm), between 0 and 1. About 0.5 for typical
     owner attempts; lower the further the typing is from the owner's.

Impostor attempts are ignored during fitting. They are still used to choose k
(cross-validation) and the threshold.
"""
import numpy as np
from scipy.spatial.distance import cdist
from sklearn.base import BaseEstimator, ClassifierMixin


class NearestNeighbourScorer(ClassifierMixin, BaseEstimator):
    def __init__(self, n_neighbors=3):
        self.n_neighbors = n_neighbors

    def fit(self, X, y):
        X, y = np.asarray(X, dtype=float), np.asarray(y)
        owner = X[y == 1]
        if len(owner) < 2:
            raise ValueError("Need at least 2 owner attempts.")
        self.classes_ = np.array([0, 1])
        self.k_ = min(self.n_neighbors, len(owner) - 1)
        self.owner_ = owner
        d = cdist(owner, owner)
        np.fill_diagonal(d, np.inf)                       # ignore distance to itself
        self.scale_ = float(np.median(np.sort(d, axis=1)[:, :self.k_].mean(axis=1)))
        return self

    def normalised_distance(self, X):
        d = cdist(np.asarray(X, dtype=float), self.owner_)
        return np.sort(d, axis=1)[:, :self.k_].mean(axis=1) / self.scale_

    def predict_proba(self, X):
        s = 1.0 / (1.0 + self.normalised_distance(X))
        return np.column_stack([1.0 - s, s])

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)

from __future__ import annotations
import abc
from dataclasses import dataclass
from typing import List, Dict
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from app.ml.features import RAW_PARAMS, model_feature_matrix
from app.core.config import ANOMALY_BANDS

CONTRIBUTOR_PARAMS = [p for p in RAW_PARAMS if p not in ("fuel_level", "solar_output")]


class AnomalyDetector(abc.ABC):
    name: str

    @abc.abstractmethod
    def fit(self, X_baseline: pd.DataFrame) -> None: ...

    @abc.abstractmethod
    def decision_scores(self, X: pd.DataFrame) -> np.ndarray:
        """Higher = more normal, lower/negative = more anomalous."""
        ...


class IsolationForestDetector(AnomalyDetector):
    name = "isolation_forest"

    def __init__(self):
        self.model = IsolationForest(n_estimators=200, contamination="auto", random_state=42)

    def fit(self, X_baseline: pd.DataFrame) -> None:
        self.model.fit(X_baseline)

    def decision_scores(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.decision_function(X)


class OneClassSVMDetector(AnomalyDetector):
    name = "one_class_svm"

    def __init__(self):
        self.model = OneClassSVM(kernel="rbf", nu=0.15, gamma="scale")
        self.scaler = StandardScaler()

    def fit(self, X_baseline: pd.DataFrame) -> None:
        Xs = self.scaler.fit_transform(X_baseline)
        self.model.fit(Xs)

    def decision_scores(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.decision_function(self.scaler.transform(X))


class AutoencoderDetector(AnomalyDetector):
    """A real (small) neural autoencoder via sklearn's MLPRegressor trained
    to reconstruct its own input. Reconstruction error is inverted so higher
    still means "more normal", matching the other detectors' convention."""
    name = "autoencoder"

    def __init__(self):
        self.model = MLPRegressor(
            hidden_layer_sizes=(8, 3, 8), activation="tanh", max_iter=800,
            random_state=42, alpha=1e-3,
        )
        self.scaler = StandardScaler()

    def fit(self, X_baseline: pd.DataFrame) -> None:
        Xs = self.scaler.fit_transform(X_baseline)
        self.model.fit(Xs, Xs)

    def decision_scores(self, X: pd.DataFrame) -> np.ndarray:
        Xs = self.scaler.transform(X)
        recon = self.model.predict(Xs)
        err = np.mean((Xs - recon) ** 2, axis=1)
        return -err


DETECTOR_REGISTRY = {
    "isolation_forest": IsolationForestDetector,
    "one_class_svm": OneClassSVMDetector,
    "autoencoder": AutoencoderDetector,
}


def get_detector(name: str) -> AnomalyDetector:
    cls = DETECTOR_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown detector '{name}'. Available: {list(DETECTOR_REGISTRY)}")
    return cls()


@dataclass
class PointResult:
    index: int
    anomaly_score: float           # 0-100
    severity_band: str
    confidence: float              # 0-1, based on baseline sample size + agreement
    contributors: List[Dict]       # top parameters driving the score


def score_band(score: float) -> str:
    if score >= ANOMALY_BANDS["CRITICAL"][0]:
        return "CRITICAL"
    if score >= ANOMALY_BANDS["WARNING"][0]:
        return "WARNING"
    if score >= ANOMALY_BANDS["LOW"][0]:
        return "LOW"
    return "NORMAL"


def raw_to_scores(raw: np.ndarray, baseline_n: int, scale: float = 55.0) -> np.ndarray:
    """Shared calibration path for every detector: normalize against the
    baseline window's own distribution of decision scores, then map to 0-100."""
    baseline_scores = raw[:baseline_n]
    lo, hi = float(baseline_scores.min()), float(baseline_scores.max())
    spread = max(hi - lo, 1e-6)
    normalized = (hi - raw) / spread
    return np.clip(normalized * scale, 0, 100)


def run_anomaly_detection(
    df: pd.DataFrame, baseline_fraction: float = 0.35, detector_name: str = "isolation_forest"
) -> List[PointResult]:
    n = len(df)
    baseline_n = max(5, int(n * baseline_fraction))
    X = model_feature_matrix(df)

    detector = get_detector(detector_name)
    detector.fit(X.iloc[:baseline_n])
    raw = detector.decision_scores(X)
    scores = raw_to_scores(np.asarray(raw), baseline_n)

    results: List[PointResult] = []
    for i in range(n):
        score = float(scores[i])
        band = score_band(score)
        confidence = float(np.clip(0.5 + 0.5 * min(baseline_n, 30) / 30, 0.5, 0.95))
        contributors = _top_contributors(df, i, baseline_n)
        results.append(PointResult(
            index=i, anomaly_score=round(score, 1), severity_band=band,
            confidence=round(confidence, 2), contributors=contributors,
        ))
    return results


def _top_contributors(df: pd.DataFrame, i: int, baseline_n: int, top_k: int = 4) -> List[Dict]:
    baseline = df.iloc[:baseline_n]
    contribs = []
    for col in CONTRIBUTOR_PARAMS:
        mu = baseline[col].mean()
        sigma = baseline[col].std() or 1e-6
        z = abs((df[col].iloc[i] - mu) / sigma)
        contribs.append((col, float(z)))
    contribs.sort(key=lambda x: x[1], reverse=True)
    total = sum(z for _, z in contribs[:top_k]) or 1e-6
    return [
        {"parameter": c, "contribution": round(z / total, 3), "z_score": round(z, 2)}
        for c, z in contribs[:top_k]
    ]

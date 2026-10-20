from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from fraudops.features import CATEGORICAL_FEATURES, MODEL_FEATURES, NUMERIC_FEATURES


@dataclass
class ModelBundle:
    model: Any
    alert_threshold: float
    model_name: str
    feature_names: list[str]
    reference: dict[str, list[float]]

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        return np.asarray(self.model.predict_proba(frame[self.feature_names])[:, 1])


def _preprocessor(scale: bool) -> ColumnTransformer:
    numeric_steps: list[tuple[str, Any]] = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))
    return ColumnTransformer(
        transformers=[
            ("numeric", Pipeline(numeric_steps), NUMERIC_FEATURES),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ]
    )


def build_baseline(seed: int = 42) -> Pipeline:
    return Pipeline(
        [
            ("prepare", _preprocessor(scale=True)),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=seed,
                ),
            ),
        ]
    )


def build_challenger(seed: int = 42) -> Pipeline:
    return Pipeline(
        [
            ("prepare", _preprocessor(scale=False)),
            (
                "model",
                HistGradientBoostingClassifier(
                    learning_rate=0.08,
                    max_iter=180,
                    max_leaf_nodes=24,
                    min_samples_leaf=18,
                    l2_regularization=0.5,
                    random_state=seed,
                ),
            ),
        ]
    )


def fit_models(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    alert_budget: float = 0.01,
    seed: int = 42,
) -> tuple[Any, ModelBundle]:
    x_train = train[MODEL_FEATURES]
    y_train = train["label"].astype(int)
    baseline = build_baseline(seed)
    challenger_base = build_challenger(seed)
    baseline.fit(x_train, y_train)
    challenger_base.fit(x_train, y_train)
    challenger = CalibratedClassifierCV(FrozenEstimator(challenger_base), method="sigmoid")
    challenger.fit(validation[MODEL_FEATURES], validation["label"].astype(int))

    validation_scores = challenger.predict_proba(validation[MODEL_FEATURES])[:, 1]
    threshold = float(np.quantile(validation_scores, 1 - alert_budget))
    reference = {
        feature: train[feature].astype(float).tolist()
        for feature in ("amount", "amount_to_avg", "is_new_device", "is_international")
    }
    bundle = ModelBundle(
        model=challenger,
        alert_threshold=threshold,
        model_name="calibrated_hist_gradient_boosting",
        feature_names=list(MODEL_FEATURES),
        reference=reference,
    )
    return baseline, bundle


def save_bundle(bundle: ModelBundle, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)


def load_bundle(path: Path) -> ModelBundle:
    loaded = joblib.load(path)
    if not isinstance(loaded, ModelBundle):
        raise TypeError("Artifact does not contain a FraudOps model bundle")
    return loaded

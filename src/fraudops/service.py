import pandas as pd

from fraudops.features import OnlineFeatureStore
from fraudops.model import ModelBundle
from fraudops.schemas import RawTransaction, ScoreResponse
from fraudops.storage import FraudRepository
from fraudops.summary import build_case_summary


class ScoringEngine:
    def __init__(self, bundle: ModelBundle, repository: FraudRepository) -> None:
        self.bundle = bundle
        self.repository = repository
        self.features = OnlineFeatureStore()

    def score(self, raw: RawTransaction) -> ScoreResponse:
        enriched = self.features.enrich(raw)
        frame = pd.DataFrame([enriched.model_dump()])
        risk_score = float(self.bundle.predict_proba(frame)[0])
        is_alert = risk_score >= self.bundle.alert_threshold
        summary = build_case_summary(enriched)
        self.repository.save_score(enriched, risk_score, is_alert, summary)
        return ScoreResponse(
            transaction_id=raw.transaction_id,
            risk_score=risk_score,
            alert=is_alert,
            alert_threshold=self.bundle.alert_threshold,
            summary=summary,
        )

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Channel = Literal["ach", "card", "wire", "instant"]


class RawTransaction(BaseModel):
    transaction_id: str
    timestamp: datetime
    account_id: str
    counterparty_id: str
    device_id: str
    amount: float = Field(gt=0)
    channel: Channel
    country: str = Field(min_length=2, max_length=2)
    home_country: str = Field(min_length=2, max_length=2)
    counterparty_age_days: float = Field(ge=0)
    label: int = Field(default=0, ge=0, le=1)
    scenario: str = "benign"


class EnrichedTransaction(RawTransaction):
    tx_count_1h: int = Field(ge=0)
    minutes_since_prev: float = Field(ge=0)
    amount_to_avg: float = Field(gt=0)
    is_new_device: int = Field(ge=0, le=1)
    is_international: int = Field(ge=0, le=1)


class EvidenceItem(BaseModel):
    evidence_id: str
    field: str
    value: str


class SupportedClaim(BaseModel):
    text: str
    evidence_ids: list[str]


class CaseSummary(BaseModel):
    observed_facts: list[SupportedClaim]
    risk_signals: list[SupportedClaim]
    missing_information: list[str]
    recommended_checks: list[str]
    evidence: list[EvidenceItem]


class ScoreResponse(BaseModel):
    transaction_id: str
    risk_score: float = Field(ge=0, le=1)
    alert: bool
    alert_threshold: float = Field(ge=0, le=1)
    summary: CaseSummary


class AlertResponse(BaseModel):
    transaction_id: str
    created_at: datetime
    risk_score: float
    scenario: str
    summary: CaseSummary

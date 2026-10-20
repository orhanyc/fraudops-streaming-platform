from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from fraudops.schemas import AlertResponse, CaseSummary, EnrichedTransaction


class Base(DeclarativeBase):
    pass


class ScoredTransaction(Base):
    __tablename__ = "scored_transactions"

    transaction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    amount: Mapped[float] = mapped_column(Float)
    channel: Mapped[str] = mapped_column(String(20))
    scenario: Mapped[str] = mapped_column(String(40))
    risk_score: Mapped[float] = mapped_column(Float, index=True)
    is_alert: Mapped[bool] = mapped_column(Boolean, index=True)
    features: Mapped[dict[str, Any]] = mapped_column(JSON)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON)


class FraudRepository:
    def __init__(self, database_url: str) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def save_score(
        self,
        transaction: EnrichedTransaction,
        score: float,
        is_alert: bool,
        summary: CaseSummary,
    ) -> None:
        record = ScoredTransaction(
            transaction_id=transaction.transaction_id,
            created_at=datetime.now(UTC),
            amount=transaction.amount,
            channel=transaction.channel,
            scenario=transaction.scenario,
            risk_score=score,
            is_alert=is_alert,
            features=transaction.model_dump(mode="json"),
            summary=summary.model_dump(mode="json"),
        )
        with Session(self.engine) as session:
            session.merge(record)
            session.commit()

    def list_alerts(self, limit: int = 50) -> list[AlertResponse]:
        statement = (
            select(ScoredTransaction)
            .where(ScoredTransaction.is_alert.is_(True))
            .order_by(ScoredTransaction.risk_score.desc())
            .limit(limit)
        )
        with Session(self.engine) as session:
            rows = session.scalars(statement).all()
        return [
            AlertResponse(
                transaction_id=row.transaction_id,
                created_at=row.created_at,
                risk_score=row.risk_score,
                scenario=row.scenario,
                summary=CaseSummary.model_validate(row.summary),
            )
            for row in rows
        ]

from fraudops.schemas import (
    CaseSummary,
    EnrichedTransaction,
    EvidenceItem,
    SupportedClaim,
)


def build_case_summary(transaction: EnrichedTransaction) -> CaseSummary:
    evidence = [
        EvidenceItem(evidence_id="ev-amount", field="amount", value=f"{transaction.amount:.2f}"),
        EvidenceItem(evidence_id="ev-channel", field="channel", value=transaction.channel),
        EvidenceItem(evidence_id="ev-country", field="country", value=transaction.country),
        EvidenceItem(
            evidence_id="ev-device",
            field="is_new_device",
            value=str(transaction.is_new_device),
        ),
        EvidenceItem(
            evidence_id="ev-velocity",
            field="tx_count_1h",
            value=str(transaction.tx_count_1h),
        ),
        EvidenceItem(
            evidence_id="ev-ratio",
            field="amount_to_avg",
            value=f"{transaction.amount_to_avg:.2f}",
        ),
        EvidenceItem(
            evidence_id="ev-counterparty",
            field="counterparty_age_days",
            value=f"{transaction.counterparty_age_days:.2f}",
        ),
    ]
    observed = [
        SupportedClaim(
            text=f"A {transaction.channel} payment for {transaction.amount:.2f} was observed.",
            evidence_ids=["ev-channel", "ev-amount"],
        ),
        SupportedClaim(
            text=f"The transaction country is {transaction.country}.",
            evidence_ids=["ev-country"],
        ),
    ]
    signals: list[SupportedClaim] = []
    if transaction.is_new_device:
        signals.append(
            SupportedClaim(text="A previously unseen device was used.", evidence_ids=["ev-device"])
        )
    if transaction.is_international:
        signals.append(
            SupportedClaim(
                text="The transaction occurred outside the account home country.",
                evidence_ids=["ev-country"],
            )
        )
    if transaction.amount_to_avg >= 3:
        signals.append(
            SupportedClaim(
                text="The amount is at least three times the prior account average.",
                evidence_ids=["ev-ratio", "ev-amount"],
            )
        )
    if transaction.tx_count_1h >= 3:
        signals.append(
            SupportedClaim(
                text="The account has multiple recent payments within one hour.",
                evidence_ids=["ev-velocity"],
            )
        )
    if transaction.counterparty_age_days <= 2:
        signals.append(
            SupportedClaim(
                text="The counterparty relationship is two days old or less.",
                evidence_ids=["ev-counterparty"],
            )
        )
    if not signals:
        signals.append(
            SupportedClaim(
                text="No individual high-risk heuristic crossed its display threshold.",
                evidence_ids=["ev-device", "ev-velocity", "ev-ratio", "ev-counterparty"],
            )
        )
    return CaseSummary(
        observed_facts=observed,
        risk_signals=signals,
        missing_information=[
            "Confirmed account-holder intent",
            "Independent device reputation",
            "Outcome from prior analyst reviews",
        ],
        recommended_checks=[
            "Verify recent account authentication changes",
            "Review the counterparty relationship history",
            "Confirm the payment through an approved customer-contact workflow",
        ],
        evidence=evidence,
    )


def summary_has_complete_citations(summary: CaseSummary) -> bool:
    available = {item.evidence_id for item in summary.evidence}
    claims = summary.observed_facts + summary.risk_signals
    return all(claim.evidence_ids and set(claim.evidence_ids) <= available for claim in claims)

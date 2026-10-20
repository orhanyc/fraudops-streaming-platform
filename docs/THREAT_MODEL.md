# Threat Model

## Protected assets

- Transaction and account identifiers
- Model artifacts and thresholds
- Analyst evidence and review outcomes
- Database and broker credentials

## Trust boundaries

The event producer, broker, scoring worker, database, API and analyst browser are separate trust boundaries. The local Compose configuration uses development credentials and is not suitable for an internet-facing deployment.

## Primary threats and controls

| Threat | Current control | Production follow-up |
|---|---|---|
| Secret disclosure | Environment-based configuration, `.gitignore`, secret scan | Managed secret store and credential rotation |
| Malformed events | Pydantic validation and bounded fields | Broker schema registry and dead-letter queue |
| Duplicate events | Transaction ID primary key and database merge | Idempotency ledger with producer sequence |
| Unauthorized API use | No public deployment is provided | OIDC, scoped roles and network policy |
| Model artifact replacement | Explicit artifact path and typed bundle check | Signed artifacts and verified provenance |
| Sensitive analyst output | Synthetic data and evidence-linked summaries | Data classification, retention and access controls |
| Denial of service | Request field limits and broker backpressure | Rate limiting, autoscaling and queue quotas |

## Residual risk

The reference UI has no authentication because it is a local portfolio demonstration. It must remain on a trusted local network unless an authentication and authorization layer is added.


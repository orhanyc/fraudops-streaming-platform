from prometheus_client import Counter, Histogram

SCORED_TRANSACTIONS = Counter(
    "fraudops_scored_transactions_total",
    "Number of scored transactions",
    ["alert"],
)
SCORING_LATENCY = Histogram(
    "fraudops_scoring_latency_seconds",
    "End-to-end transaction scoring latency",
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)
SCORING_ERRORS = Counter(
    "fraudops_scoring_errors_total",
    "Number of failed scoring requests",
)

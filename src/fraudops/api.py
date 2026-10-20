import asyncio
import os
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from fraudops.model import ModelBundle, load_bundle
from fraudops.schemas import AlertResponse, RawTransaction, ScoreResponse
from fraudops.service import ScoringEngine
from fraudops.storage import FraudRepository
from fraudops.telemetry import SCORED_TRANSACTIONS, SCORING_ERRORS, SCORING_LATENCY

MODEL_PATH = Path(os.getenv("FRAUDOPS_MODEL_PATH", "artifacts/model.joblib"))
DATABASE_URL = os.getenv("FRAUDOPS_DATABASE_URL", "sqlite:///fraudops.db")
repository = FraudRepository(DATABASE_URL)
feature_lock = asyncio.Lock()
model_bundle: ModelBundle | None = None
scoring_engine: ScoringEngine | None = None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global model_bundle, scoring_engine
    repository.create_schema()
    if MODEL_PATH.exists():
        model_bundle = load_bundle(MODEL_PATH)
        scoring_engine = ScoringEngine(model_bundle, repository)
    yield


app = FastAPI(
    title="FraudOps Streaming Platform",
    version="0.1.0",
    description=(
        "Synthetic payment scoring with an analyst alert budget and evidence-linked summaries."
    ),
    lifespan=lifespan,
)


@app.middleware("http")
async def request_trace(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["x-trace-id"] = trace_id
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ready" if model_bundle is not None else "model_missing",
        "model": model_bundle.model_name if model_bundle else "none",
    }


@app.post("/score", response_model=ScoreResponse)
async def score(raw: RawTransaction) -> ScoreResponse:
    if scoring_engine is None:
        raise HTTPException(status_code=503, detail="Model artifact is not available")
    started = time.perf_counter()
    try:
        async with feature_lock:
            result = scoring_engine.score(raw)
        SCORED_TRANSACTIONS.labels(alert=str(result.alert).lower()).inc()
        return result
    except Exception:
        SCORING_ERRORS.inc()
        raise
    finally:
        SCORING_LATENCY.observe(time.perf_counter() - started)


@app.get("/alerts", response_model=list[AlertResponse])
async def alerts(limit: int = 50) -> list[AlertResponse]:
    return repository.list_alerts(min(max(limit, 1), 200))


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", response_class=HTMLResponse)
async def analyst_ui() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FraudOps Analyst Queue</title>
  <style>
    body { font: 16px system-ui; margin: 0; background: #0b1020; color: #e7ecf5; }
    main { max-width: 1000px; margin: 40px auto; padding: 0 20px; }
    h1 { font-size: 30px; } .sub { color: #9fb0c9; }
    table { width: 100%; border-collapse: collapse; background: #141c2f; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #29344c; }
    th { color: #8ed0ff; } .score { font-variant-numeric: tabular-nums; color: #ffbd69; }
  </style>
</head>
<body><main>
  <h1>FraudOps Analyst Queue</h1>
  <p class="sub">Synthetic alerts ranked by calibrated risk score.</p>
  <table><thead><tr><th>Transaction</th><th>Score</th><th>Scenario</th>
  <th>Top signal</th></tr></thead>
  <tbody id="alerts"><tr><td colspan="4">No alerts scored yet.</td></tr></tbody></table>
  <script>
    fetch('/alerts').then(r => r.json()).then(items => {
      if (!items.length) return;
      document.querySelector('#alerts').innerHTML = items.map(item => `<tr>
        <td>${item.transaction_id}</td><td class="score">${item.risk_score.toFixed(4)}</td>
        <td>${item.scenario}</td><td>${item.summary.risk_signals[0].text}</td></tr>`).join('');
    });
  </script>
</main></body></html>
"""

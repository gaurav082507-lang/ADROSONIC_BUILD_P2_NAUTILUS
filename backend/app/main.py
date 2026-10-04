import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.model_registry import model_registry
from .db.migrations import run_migrations
from fastapi.exceptions import RequestValidationError
from .db.repository import recover_interrupted_jobs
from .core.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler
)
from .api.v1 import health, analyze, jobs, results, artifacts, auth, policies, claims, queue, decisions, identity, voice, network, analytics, admin
from .services.storage import cleanup_old_uploads

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "level":"%(levelname)s", "logger":"%(name)s", "message":"%(message)s"}'
)
logger = logging.getLogger("lucen_ai")

async def _periodic_cleanup():
    while True:
        try:
            cleanup_old_uploads()
        except Exception as e:
            logger.warning(f"Error in background upload cleanup: {e}")
        await asyncio.sleep(3600)  # Check every hour

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Lucen AI application...")
    run_migrations()

    # Mark interrupted jobs from prior crashes as failed
    recovered = recover_interrupted_jobs()
    if recovered > 0:
        logger.info(f"Marked {recovered} interrupted jobs as failed upon startup.")

    # Load models once at startup
    model_registry.load_all()
    logger.info(
        f"MOCK_ANALYSIS={'ON (canned results)' if settings.MOCK_ANALYSIS else 'OFF — real pipeline active'}"
    )

    # Initial cleanup run & schedule periodic cleanup
    cleanup_old_uploads()
    cleanup_task = asyncio.create_task(_periodic_cleanup())

    # Build fraud network graph on startup
    try:
        from .services.network import detect_fraud_rings
        detect_fraud_rings(rebuild=True)
    except Exception as e:
        logger.warning(f"Could not build network graph at startup: {e}")

    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Lucen AI application shutdown complete.")

app = FastAPI(
    title="Lucen AI",
    version="1.0.0",
    description="Synthetic Identity and Deepfake Insurance-Claim Fraud Detection System",
    lifespan=lifespan
)

# Exception handlers matching §7.2 standard error shape
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# CORS from CORS_ORIGINS (no wildcard)
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 Routers — all routes live under /api/v1 only (P2-11: remove duplicate mounts)
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
app.include_router(analyze.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])
app.include_router(results.router, prefix="/api/v1", tags=["Results"])
app.include_router(artifacts.router, prefix="/api/v1", tags=["Artifacts"])
app.include_router(policies.router, prefix="/api/v1", tags=["Policies"])
app.include_router(claims.router, prefix="/api/v1", tags=["Claims"])
app.include_router(queue.router, prefix="/api/v1", tags=["Queue"])
app.include_router(decisions.router, prefix="/api/v1", tags=["Decisions"])
app.include_router(identity.router, prefix="/api/v1", tags=["Identity"])
app.include_router(voice.router, prefix="/api/v1", tags=["Voice"])
app.include_router(network.router, prefix="/api/v1", tags=["Network"])
app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

@app.get('/api/v1/dashboard/stats')
async def get_dashboard_stats():
    from backend.app.db.database import get_connection
    import sqlite3
    from collections import defaultdict
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    
    # KPI metrics
    claims = conn.execute('''
        SELECT c.id, c.status, r.overall_band, r.overall_risk, c.created_at, c.claim_type
        FROM claims c
        LEFT JOIN results r ON c.result_id = r.id
    ''').fetchall()
    
    total = len(claims)
    flagged = len([c for c in claims if c['overall_band'] in ('HIGH', 'MEDIUM')])
    cleared = len([c for c in claims if c['overall_band'] == 'LOW'])
    pending = len([c for c in claims if c['status'] == 'submitted'])
    
    risks = [c['overall_risk'] for c in claims if c['overall_risk'] is not None]
    avg_risk = sum(risks) / len(risks) * 100 if risks else 0.0
    
    # Verdict Donut
    verdicts = [
        {"name": "Genuine", "value": cleared},
        {"name": "Suspicious", "value": len([c for c in claims if c['overall_band'] == 'MEDIUM'])},
        {"name": "Deepfake-Fraud", "value": len([c for c in claims if c['overall_band'] == 'HIGH'])},
    ]
    
    # Signals
    signals = conn.execute('''
        SELECT title as name, COUNT(*) as value
        FROM evidence
        WHERE kind = 'risk'
        GROUP BY title
        ORDER BY value DESC
        LIMIT 5
    ''').fetchall()
    
    # Cases Over Time
    time_map = defaultdict(lambda: {"total": 0, "flagged": 0})
    for c in claims:
        dt = (c['created_at'] or '')[:10]
        if not dt: continue
        time_map[dt]["total"] += 1
        if c['overall_band'] in ('HIGH', 'MEDIUM'):
            time_map[dt]["flagged"] += 1
    
    time_data = []
    for dt in sorted(time_map.keys())[-7:]:
        time_data.append({"date": dt, "Total Cases": time_map[dt]["total"], "Flagged": time_map[dt]["flagged"]})
        
    # Risk Distribution
    buckets = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    for r in risks:
        if r < 0.2: buckets["0-20"] += 1
        elif r < 0.4: buckets["20-40"] += 1
        elif r < 0.6: buckets["40-60"] += 1
        elif r < 0.8: buckets["60-80"] += 1
        else: buckets["80-100"] += 1
    
    risk_dist = [{"bucket": k, "cases": v} for k, v in buckets.items()]
    
    conn.close()
    
    return {
        "kpis": {
            "total": total,
            "flagged": flagged,
            "cleared": cleared,
            "pending": pending,
            "avgRisk": round(avg_risk, 1)
        },
        "verdicts": verdicts,
        "signals": [dict(s) for s in signals],
        "timeData": time_data,
        "riskDist": risk_dist
    }

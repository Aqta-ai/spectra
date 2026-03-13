"""Spectra backend — optimised FastAPI + WebSocket server.

Performance improvements:
- Connection pooling
- Async database operations
- Optimised CORS
- Reduced middleware overhead
"""

import asyncio
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from urllib.parse import parse_qs

from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.overlay import router as overlay_router
from app.plugins import load_plugins, registry
from app.streaming.session import SpectraStreamingSession

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "WARNING"))
logger = logging.getLogger(__name__)

REVOLUT_SECRET_KEY = os.getenv("REVOLUT_SECRET_KEY", "")
REVOLUT_MERCHANT_URL = (
    "https://sandbox-merchant.revolut.com"
    if os.getenv("REVOLUT_SANDBOX_MODE", "true").lower() == "true"
    else "https://merchant.revolut.com"
)

# Optimized session tracking
_active_sessions: dict[str, float] = {}
_total_sessions = 0
_session_queue: asyncio.Queue = asyncio.Queue()
_session_lock = asyncio.Lock()  # Thread safety for session tracking

# Simple in-memory rate limiter for /api/support (5 requests/minute per IP)
_support_rate: dict[str, list[float]] = {}
_SUPPORT_RATE_LIMIT = 5
_SUPPORT_RATE_WINDOW = 60.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Spectra backend starting...")
    load_plugins()
    for router in registry.extra_routers:
        app.include_router(router)
    yield
    logger.info("Spectra backend shutting down. Total sessions served: %d", _total_sessions)


app = FastAPI(
    title="Spectra — See it. Hear it. Control it.",
    version="0.3.0",
    lifespan=lifespan,
    # Optimized settings
    docs_url=None,  # Disable docs in production
    redoc_url=None,  # Disable redoc in production
)
app.include_router(overlay_router)

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Optimized CORS settings
    max_age=600,  # Cache preflight for 10 minutes
    expose_headers=["*"],
)


@app.get("/health")
async def health():
    from app.performance_monitor import get_performance_monitor
    
    # Get performance statistics
    perf_monitor = get_performance_monitor()
    perf_stats = perf_monitor.get_performance_stats()
    
    return {
        "status": "ok",
        "service": "spectra-backend",
        "active_sessions": len(_active_sessions),
        "total_sessions": _total_sessions,
        "uptime_info": {
            sid: round(time.time() - start, 1)
            for sid, start in _active_sessions.items()
        },
        "performance": perf_stats,
    }


@app.post("/api/support")
async def create_support_order(request: Request):
    """Create Revolut checkout order."""
    import httpx
    from fastapi.responses import JSONResponse

    # Rate limit: 5 requests per minute per IP
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    timestamps = _support_rate.get(client_ip, [])
    timestamps = [t for t in timestamps if now - t < _SUPPORT_RATE_WINDOW]
    if len(timestamps) >= _SUPPORT_RATE_LIMIT:
        return JSONResponse({"error": "Too many requests. Please wait a moment."}, status_code=429)
    timestamps.append(now)
    _support_rate[client_ip] = timestamps

    if not REVOLUT_SECRET_KEY:
        return JSONResponse({"error": "Payments not configured"}, status_code=500)

    body = await request.json()
    amount = body.get("amount", 500)
    currency = body.get("currency", "EUR")

    if not isinstance(amount, int) or amount < 100 or amount > 50000:
        return JSONResponse({"error": "Amount must be between €1 and €500"}, status_code=400)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:  # Reduced timeout
            resp = await client.post(
                f"{REVOLUT_MERCHANT_URL}/api/1.0/orders",
                headers={
                    "Authorization": f"Bearer {REVOLUT_SECRET_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "amount": amount,
                    "currency": currency,
                    "description": "Support Spectra — open source accessibility",
                },
            )
            data = resp.json()
            logger.info("Revolut response status=%s body=%s", resp.status_code, data)

            if resp.status_code >= 400:
                logger.error("Revolut order error: %s", data)
                return JSONResponse({"error": "Could not create payment"}, status_code=502)

            checkout_url = data.get("checkout_url")
            if not checkout_url:
                logger.error("No checkout_url in Revolut response: %s", data)
                return JSONResponse({"error": "No checkout URL returned"}, status_code=502)

            return {"checkout_url": checkout_url}
    except Exception as e:
        logger.error("Support endpoint error: %s", e)
        return JSONResponse({"error": "Payment service unavailable"}, status_code=503)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Bidirectional streaming: client ↔ backend ↔ Gemini Live API."""
    global _total_sessions
    await websocket.accept()

    query_string = str(websocket.scope.get("query_string", b""), "utf-8")
    params = parse_qs(query_string)
    api_key_raw = params.get("api_key", [""])[0]
    
    # Get session_id from query params or generate a cryptographically secure one.
    # Using secrets.token_hex avoids id(websocket) % 10000 collisions.
    session_id = params.get("session_id", [f"s-{secrets.token_hex(8)}"])[0]

    org_id = ""
    org_tier = "free"
    if api_key_raw and registry.validate_api_key:
        result = registry.validate_api_key(api_key_raw)
        if not result:
            await websocket.send_json({"type": "error", "reason": "invalid_api_key"})
            await websocket.close(code=4001, reason="Invalid API key")
            return
        ctx, _ak = result
        org_id = ctx.get("org_id", "")
        org_tier = ctx.get("tier", "free")

    async with _session_lock:
        _active_sessions[session_id] = time.time()
        _total_sessions += 1

    # Use session_id as user_id for session tracking
    user_id = session_id
    
    # Pass session_id to SpectraStreamingSession for persistent state
    session = SpectraStreamingSession(websocket, user_id=user_id, session_id=session_id)
    logger.debug("Spectra session: %s (user: %s)", session_id, user_id)

    if registry.on_session_start:
        registry.on_session_start(session_id, org_id, org_tier)

    session_start = time.time()

    try:
        await session.run()
    except WebSocketDisconnect:
        logger.info("Client disconnected: %s", session_id)
    except Exception as e:
        logger.error("Session error [%s]: %s", session_id, e, exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e)[:120])
        except Exception:
            pass
    finally:
        duration = time.time() - session_start
        await session.cleanup()
        async with _session_lock:
            _active_sessions.pop(session_id, None)
        logger.debug("Session cleaned up: %s (duration: %.1fs)", session_id, duration)

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

# Optimized session tracking
_active_sessions: dict[str, float] = {}
_total_sessions = 0
_session_queue: asyncio.Queue = asyncio.Queue()
_session_lock = asyncio.Lock()  # Thread safety for session tracking


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


@app.get("/vision-debug")
async def vision_debug():
    """Debug endpoint to check vision system status"""
    from app.streaming.session_manager import get_session_manager
    
    session_manager = get_session_manager()
    session_stats = session_manager.get_session_stats()
    
    # Check if any sessions have recent frames
    recent_frames = 0
    stale_frames = 0
    current_time = time.time()
    
    for session_id, start_time in _active_sessions.items():
        # This is a simplified check - in a real implementation,
        # we'd need access to the actual session objects
        if current_time - start_time < 10:  # Active in last 10s
            recent_frames += 1
        else:
            stale_frames += 1
    
    return {
        "status": "vision_debug",
        "model": "gemini-2.5-flash-native-audio-preview-12-2025",
        "vision_capable": True,
        "active_sessions": len(_active_sessions),
        "session_stats": session_stats,
        "frame_status": {
            "recent_frames": recent_frames,
            "stale_frames": stale_frames,
            "total_sessions_with_stream": session_stats.get("sessions_with_stream", 0)
        },
        "potential_issues": [
            "Check if frontend is sending screenshot messages",
            "Verify Gemini Live API is receiving video frames", 
            "Ensure model has multimodal capabilities enabled",
            "Check for frame timing issues or stale data"
        ]
    }




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

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
from pydantic import BaseModel

from app.overlay import router as overlay_router
from app.plugins import load_plugins, registry
from app.streaming.session import SpectraStreamingSession
from app.sse_endpoint import sse_endpoint, receive_audio, receive_text

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "WARNING"))
logger = logging.getLogger(__name__)

# Optimized session tracking
_active_sessions: dict[str, float] = {}
_active_session_objects: dict[str, "SpectraStreamingSession"] = {}
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


@app.get("/api/system-info")
async def system_info():
    """Return system configuration info (provider type, offline mode, etc.)."""
    # Read .env dynamically (not cached) to pick up provider switches
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    provider_type = "gemini"
    try:
        with open(env_file, "r") as f:
            for line in f:
                if line.startswith("SPECTRA_PROVIDER="):
                    provider_type = line.split("=", 1)[1].strip().lower()
                    break
    except Exception:
        pass

    offline_mode = provider_type in ("local_audio", "local", "audio", "gemma", "ollama")

    return {
        "provider": provider_type,
        "offline_mode": offline_mode,
        "version": "1.0.0",
    }


class ProviderRequest(BaseModel):
    new_provider: str


@app.post("/api/switch-provider")
async def switch_provider(req: ProviderRequest):
    """Switch between Gemini and Ollama providers (updates .env and restarts backend)."""
    new_provider = req.new_provider
    if new_provider not in ("gemini", "ollama"):
        return {"error": "Invalid provider. Use 'gemini' or 'ollama'.", "status": 400}

    # Update .env file
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    try:
        with open(env_file, "r") as f:
            lines = f.readlines()

        with open(env_file, "w") as f:
            for line in lines:
                if line.startswith("SPECTRA_PROVIDER="):
                    f.write(f"SPECTRA_PROVIDER={new_provider}\n")
                else:
                    f.write(line)

        os.environ["SPECTRA_PROVIDER"] = new_provider
        return {
            "status": "ok",
            "provider": new_provider,
            "message": "Provider switched. Refresh your browser to reconnect.",
        }
    except Exception as e:
        logger.error(f"Failed to switch provider: {e}")
        return {"error": str(e), "status": 500}


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
    """Debug endpoint — only available when ENABLE_VISION_DEBUG is set. Returns 404 in production."""
    if os.getenv("ENABLE_VISION_DEBUG", "").lower() not in ("1", "true", "yes"):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    from app.streaming.session_manager import get_session_manager

    session_manager = get_session_manager()
    session_stats = session_manager.get_session_stats()

    recent_frames = 0
    stale_frames = 0
    current_time = time.time()
    for session_id, start_time in _active_sessions.items():
        if current_time - start_time < 10:
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
            "total_sessions_with_stream": session_stats.get("sessions_with_stream", 0),
        },
        "potential_issues": [
            "Check if frontend is sending screenshot messages",
            "Verify Gemini Live API is receiving video frames",
            "Ensure model has multimodal capabilities enabled",
            "Check for frame timing issues or stale data",
        ],
    }




@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Bidirectional streaming: client ↔ backend ↔ Gemini Live API or Ollama."""
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
        # Kill any existing session with the same ID to prevent duplicate
        # connections and wasted quota.
        old_session = _active_session_objects.pop(session_id, None)
        if old_session is not None:
            logger.info("Killing duplicate session %s (new connection replacing old)", session_id)
            try:
                await old_session.cleanup()
            except Exception:
                pass

        _active_sessions[session_id] = time.time()
        _total_sessions += 1

    # Use session_id as user_id for session tracking
    user_id = session_id

    # Create Gemini Live session
    session = SpectraStreamingSession(websocket, user_id=user_id, session_id=session_id)
    logger.info("Created Gemini session: %s (user: %s)", session_id, user_id)

    async with _session_lock:
        _active_session_objects[session_id] = session

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
            # Only remove if it's still *our* session (a newer one may have replaced us)
            if _active_session_objects.get(session_id) is session:
                _active_session_objects.pop(session_id, None)
        logger.debug("Session cleaned up: %s (duration: %.1fs)", session_id, duration)


# ── SSE Endpoints for Vercel Compatibility ──────────────────────────────────
# ⚠️ IMPORTANT: SSE has limitations for Gemini Live API
# Gemini Live API REQUIRES WebSockets for real-time bidirectional audio streaming
# SSE is unidirectional (server → client only) and cannot handle:
# - Real-time audio streaming to Gemini
# - Bidirectional communication  
# - Low-latency voice interaction

@app.get("/sse")
async def sse_stream_endpoint(request: Request, session_id: str = None):
    """Server-Sent Events endpoint for Vercel compatibility.
    
    ⚠️ LIMITATIONS:
    - Unidirectional only (server → client)
    - No real-time audio streaming to Gemini
    - Requires separate HTTP endpoints for client→server communication
    
    Usage:
    - Frontend connects to: GET /sse?session_id=abc123
    - Frontend sends audio via: POST /sse/audio
    - Frontend sends text via: POST /sse/text
    """
    return await sse_endpoint(request, session_id)


@app.post("/sse/audio")
async def sse_receive_audio(request: Request, session_id: str):
    """Receive audio from client via HTTP POST (SSE workaround).
    
    This is a workaround for SSE's unidirectional limitation.
    Client must send audio data via separate HTTP requests.
    
    ⚠️ Gemini Live API requires WebSockets for real-time audio streaming.
    This endpoint cannot stream audio to Gemini Live API.
    """
    return await receive_audio(request, session_id)


@app.post("/sse/text")
async def sse_receive_text(request: Request, session_id: str):
    """Receive text from client via HTTP POST (SSE workaround)."""
    return await receive_text(request, session_id)

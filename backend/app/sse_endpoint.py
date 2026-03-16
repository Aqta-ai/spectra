"""Server-Sent Events (SSE) endpoint for Vercel compatibility.

⚠️ IMPORTANT LIMITATION:
Gemini Live API REQUIRES WebSockets for real-time bidirectional audio streaming.
SSE is unidirectional (server → client only) and cannot handle:
- Real-time audio streaming to Gemini
- Bidirectional communication
- Low-latency voice interaction

This endpoint provides a fallback for Vercel deployment but with reduced functionality.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)


async def sse_stream(request: Request, session_id: str) -> AsyncGenerator[str, None]:
    """SSE stream for Vercel compatibility.
    
    This provides a unidirectional stream from server to client.
    Client must use HTTP POST for sending audio/text to the server.
    
    Args:
        request: FastAPI request object
        session_id: Session identifier
        
    Yields:
        SSE events in format: "data: {json_data}\n\n"
    """
    try:
        # Send connection established event
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        
        # Simulate heartbeat (SSE doesn't support client→server communication)
        heartbeat_count = 0
        while not await request.is_disconnected():
            heartbeat_count += 1
            
            # Send heartbeat event
            heartbeat_data = {
                'type': 'heartbeat',
                'count': heartbeat_count,
                'message': 'SSE connection active (limited functionality)'
            }
            yield f"data: {json.dumps(heartbeat_data)}\n\n"
            
            # Wait before next heartbeat
            await asyncio.sleep(5.0)
            
    except asyncio.CancelledError:
        logger.info(f"SSE stream cancelled for session {session_id}")
    except Exception as e:
        logger.error(f"SSE stream error for session {session_id}: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


async def sse_endpoint(request: Request, session_id: str = None):
    """SSE endpoint for Vercel deployment.
    
    This endpoint works with Vercel/Next.js API routes but has limitations:
    1. Unidirectional only (server → client)
    2. No real-time audio streaming to Gemini
    3. Requires separate HTTP endpoints for client→server communication
    
    Usage:
    - Frontend connects to: GET /sse?session_id=abc123
    - Frontend sends audio via: POST /sse/audio
    - Frontend sends text via: POST /sse/text
    
    Returns:
        EventSourceResponse for SSE streaming
    """
    if not session_id:
        session_id = f"sse-{asyncio.get_event_loop().time()}"
    
    logger.info(f"SSE connection established for session {session_id}")
    
    return EventSourceResponse(
        sse_stream(request, session_id),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )


async def receive_audio(request: Request, session_id: str):
    """Receive audio from client via HTTP POST.
    
    This is a workaround for SSE's unidirectional limitation.
    Client must send audio data via separate HTTP requests.
    
    Args:
        request: FastAPI request with audio data
        session_id: Session identifier
        
    Returns:
        JSON response with status
    """
    try:
        data = await request.json()
        audio_data = data.get("audio")  # Base64 encoded audio
        
        if not audio_data:
            return {"status": "error", "message": "No audio data provided"}
        
        # In a real implementation, this would forward to Gemini
        # But Gemini Live API requires WebSockets for audio streaming
        logger.info(f"Received audio for session {session_id} (size: {len(audio_data)})")
        
        return {
            "status": "received",
            "session_id": session_id,
            "message": "Audio received (SSE cannot stream to Gemini Live API)",
            "limitation": "Gemini Live API requires WebSockets for real-time audio streaming"
        }
        
    except Exception as e:
        logger.error(f"Error receiving audio for session {session_id}: {e}")
        return {"status": "error", "message": str(e)}


async def receive_text(request: Request, session_id: str):
    """Receive text from client via HTTP POST.
    
    Args:
        request: FastAPI request with text data
        session_id: Session identifier
        
    Returns:
        JSON response with status
    """
    try:
        data = await request.json()
        text = data.get("text", "")
        
        if not text:
            return {"status": "error", "message": "No text provided"}
        
        logger.info(f"Received text for session {session_id}: '{text[:50]}...'")
        
        # Simulate processing (in real implementation, this would go to Gemini)
        return {
            "status": "received",
            "session_id": session_id,
            "text": text,
            "response": "Text received via SSE fallback (limited functionality)",
            "warning": "Full voice interaction requires WebSockets for Gemini Live API"
        }
        
    except Exception as e:
        logger.error(f"Error receiving text for session {session_id}: {e}")
        return {"status": "error", "message": str(e)}
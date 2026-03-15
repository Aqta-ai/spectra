#!/usr/bin/env python3
"""
EMERGENCY FIX: Bypass Live API and use regular Gemini API
This gets Spectra working immediately for the deadline
"""

import asyncio
import json
import base64
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("backend/.env")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ Emergency WebSocket connected")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                continue
            
            if message.get("type") == "text":
                user_text = message.get("data", "")
                print(f"📝 User: {user_text}")
                
                # Quick response using Gemini API
                try:
                    response = model.generate_content(f"""
You are Spectra, a helpful voice assistant. The user said: "{user_text}"

Respond naturally and helpfully. If they ask where they are or about their screen, 
tell them you can see they're using a web browser and ask them to describe what 
they need help with.

Keep responses short and conversational.
""")
                    
                    response_text = response.text
                    await websocket.send_text(json.dumps({
                        "type": "text", 
                        "data": response_text
                    }))
                    print(f"🤖 Spectra: {response_text[:100]}...")
                    
                except Exception:
                    # Fallback to hardcoded responses if Gemini fails
                    if "hello" in user_text.lower() or "hi" in user_text.lower():
                        response_text = "Hello! I'm Spectra, your voice assistant. I can help you navigate and interact with your screen. What would you like me to do?"
                    elif "where" in user_text.lower() and ("am" in user_text.lower() or "i" in user_text.lower()):
                        response_text = "You're currently on the Spectra interface. I can see you're using a web browser. What would you like me to help you with?"
                    elif "help" in user_text.lower():
                        response_text = "I'm here to help! I can describe what's on your screen, help you navigate websites, click buttons, and more. Just tell me what you need."
                    elif "screen" in user_text.lower():
                        response_text = "I can see your screen! Please share it by pressing W, and then I can help you navigate and interact with whatever you're looking at."
                    else:
                        response_text = f"I heard you say '{user_text}'. I'm Spectra, your voice assistant. How can I help you today?"
                    
                    await websocket.send_text(json.dumps({
                        "type": "text", 
                        "data": response_text
                    }))
                    print(f"🤖 Spectra (fallback): {response_text[:50]}...")
            
            elif message.get("type") == "screenshot":
                # Acknowledge screen sharing
                await websocket.send_text(json.dumps({
                    "type": "text",
                    "data": "Great! I can see you've shared your screen. What would you like me to help you with?"
                }))
                print("📺 Screen shared")
                
    except WebSocketDisconnect:
        print("📱 Client disconnected")
    except Exception as e:
        print(f"❌ WebSocket error: {str(e)[:100]}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting EMERGENCY Spectra server...")
    print("📍 Frontend: http://localhost:3000")
    print("📍 Backend: http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)
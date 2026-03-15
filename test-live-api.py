#!/usr/bin/env python3
"""
Test Gemini Live API connection with the fixed model name
"""

import asyncio
import websockets
import json

async def test_live_api():
    uri = "ws://localhost:8080/ws"
    
    try:
        print("🔌 Connecting to Spectra with Gemini Live API...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # Send a test message
            test_message = {
                "type": "text",
                "data": "Hello Spectra, test the live API"
            }
            
            print(f"📤 Sending: {test_message['data']}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response with timeout
            print("⏳ Waiting for Gemini Live API response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                print(f"📥 Received: {response_data}")
                
                if response_data.get("type") == "text":
                    print(f"🤖 Spectra (Live API): {response_data.get('data')}")
                    print("✅ SUCCESS: Gemini Live API is working!")
                elif response_data.get("type") == "audio":
                    print("🎵 Received audio response from Live API!")
                    print("✅ SUCCESS: Gemini Live API with audio is working!")
                else:
                    print(f"📋 Response type: {response_data.get('type')}")
                    
            except asyncio.TimeoutError:
                print("⏰ Timeout - Live API might be connecting...")
                print("💡 Try again or check if model is available")
                
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("💡 The Live API model might not be available yet")
        print("💡 Falling back to emergency backend might be needed")

if __name__ == "__main__":
    asyncio.run(test_live_api())
#!/usr/bin/env python3
"""
Quick test to verify Spectra emergency backend is working
"""

import asyncio
import websockets
import json

async def test_spectra():
    uri = "ws://localhost:8080/ws"
    
    try:
        print("🔌 Connecting to Spectra...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # Send a test message
            test_message = {
                "type": "text",
                "data": "Hello Spectra, are you working?"
            }
            
            print(f"📤 Sending: {test_message['data']}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            print("⏳ Waiting for response...")
            response = await websocket.recv()
            response_data = json.loads(response)
            
            print(f"📥 Received: {response_data}")
            
            if response_data.get("type") == "text":
                print(f"🤖 Spectra says: {response_data.get('data')}")
                print("✅ SUCCESS: Spectra is working!")
            else:
                print("❌ Unexpected response format")
                
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("Make sure the emergency backend is running: python3 emergency-fix.py")

if __name__ == "__main__":
    asyncio.run(test_spectra())
#!/usr/bin/env python3
"""Backend smoke test for the minimal Navis API."""

import sys
import time
import requests
from subprocess import Popen, PIPE
import signal

def test_backend():
    """Test backend startup, health check, and basic analysis flow."""
    
    print("🚀 Starting Navis backend...")
    
    # Start the backend process
    process = Popen(
        ["python", "navis-backend/main.py"],
        stdout=PIPE,
        stderr=PIPE,
        text=True
    )
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    max_attempts = 15
    for attempt in range(max_attempts):
        time.sleep(1)
        try:
            response = requests.get("http://127.0.0.1:8000/", timeout=1)
            if response.status_code == 200:
                print(f"✅ Server started after {attempt + 1} seconds")
                break
        except:
            if attempt < max_attempts - 1:
                print(f"   Attempt {attempt + 1}/{max_attempts}...")
            else:
                print("❌ Server failed to start")
                process.kill()
                return False
    
    try:
        print("🔍 Testing health endpoint...")
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code != 200:
            print(f"\n❌ Health check failed with status {response.status_code}")
            return False

        health_data = response.json()
        print("\n✅ Backend is healthy!")
        print(f"   Version: {health_data.get('version')}")
        print(f"   Status: {health_data.get('status')}")

        print("\n📊 Component Status:")
        components = health_data.get('components', {})
        for name, status in components.items():
            icon = "✅" if status else "⚠️"
            print(f"   {icon} {name}: {status}")

        print("\n🧪 Creating session...")
        session_response = requests.post(
            "http://127.0.0.1:8000/sessions",
            json={"metadata": {"source": "smoke-test"}},
            timeout=5,
        )
        session_response.raise_for_status()
        session_id = session_response.json()["session_id"]
        print(f"   ✅ Session created: {session_id}")

        print("\n🧠 Parsing intent...")
        intent_response = requests.post(
            "http://127.0.0.1:8000/intent/parse",
            json={
                "session_id": session_id,
                "user_goal": "click login button",
                "page_context": {"title": "Example Login", "url": "https://example.com/login"},
            },
            timeout=5,
        )
        intent_response.raise_for_status()
        intent_data = intent_response.json()
        print(f"   ✅ Parsed intent: {intent_data.get('action_type')} -> {intent_data.get('target')}")

        print("\n🎯 Running semantic analysis...")
        analyze_response = requests.post(
            "http://127.0.0.1:8000/semantic/analyze",
            json={
                "session_id": session_id,
                "user_goal": "click login button",
                "page_context": {"title": "Example Login", "url": "https://example.com/login"},
                "elements": [
                    {"selector": "#login", "tag": "button", "text": "Login", "is_visible": True, "is_enabled": True, "position": {"y": 120}},
                    {"selector": "#forgot", "tag": "a", "text": "Forgot password", "is_visible": True, "is_enabled": True, "position": {"y": 320}},
                ],
            },
            timeout=5,
        )
        analyze_response.raise_for_status()
        analysis = analyze_response.json()
        selected = analysis["decision"]["selected"]
        print(f"   ✅ Selected candidate: {selected['selector']} ({selected['text']})")

        print("\n✅ All tests passed!")
        return True
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to backend")
        print("   Make sure the backend is running on http://127.0.0.1:8000")
        return False
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False
        
    finally:
        # Stop the backend
        print("\n🛑 Stopping backend...")
        process.send_signal(signal.SIGINT)
        process.wait(timeout=5)
        print("✅ Backend stopped")

if __name__ == "__main__":
    success = test_backend()
    sys.exit(0 if success else 1)

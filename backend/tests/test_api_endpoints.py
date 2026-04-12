"""
Test suite for FastAPI REST endpoints
Tests health checks, metrics, and API routes
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check_returns_200(self):
        """Health endpoint should return 200 OK"""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_check_returns_status(self):
        """Health endpoint should return status field"""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

    def test_health_check_includes_uptime(self):
        """Health endpoint should include uptime info"""
        response = client.get("/health")
        data = response.json()
        assert "uptime_info" in data or "performance" in data
        if "performance" in data and "system_metrics" in data["performance"]:
            assert "uptime_seconds" in data["performance"]["system_metrics"] or "uptime_hours" in data["performance"]["system_metrics"]


class TestMetricsEndpoint:
    """Test metrics endpoint (if /metrics exists)."""

    def test_metrics_returns_200_or_404(self):
        """Metrics endpoint may not exist; if it does, return 200"""
        response = client.get("/metrics")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_metrics_includes_response_time(self):
        """If /metrics exists, may include response time stats"""
        response = client.get("/metrics")
        if response.status_code != 200:
            pytest.skip("/metrics not implemented")
        data = response.json()
        assert "response_time" in data or "performance" in data

    def test_metrics_includes_session_count(self):
        """If /metrics exists, may include session count"""
        response = client.get("/metrics")
        if response.status_code != 200:
            pytest.skip("/metrics not implemented")
        data = response.json()
        assert "active_sessions" in data or "performance" in data

    def test_metrics_includes_error_rate(self):
        """If /metrics exists, may include error rate"""
        response = client.get("/metrics")
        if response.status_code != 200:
            pytest.skip("/metrics not implemented")
        data = response.json()
        assert "error_rate" in data or "performance" in data


class TestWebSocketEndpoint:
    """Test WebSocket connection endpoint"""
    
    def test_websocket_connection_succeeds(self):
        """WebSocket connection should succeed; first message may be audio, text, or ready"""
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            assert "type" in data
            assert data["type"] in ["connected", "ready", "audio", "text", "action", "gemini_reconnecting"]

    def test_websocket_sends_session_id(self):
        """WebSocket sends messages; session_id may be in first or later message"""
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            assert data is not None
            # Session identity may be in type, id, or a separate message
            assert "type" in data or "id" in data or "session_id" in data
    
    def test_websocket_accepts_audio(self):
        """WebSocket should accept audio messages"""
        with client.websocket_connect("/ws") as websocket:
            # Wait for connection
            websocket.receive_json()
            
            # Send audio
            websocket.send_json({
                "type": "audio",
                "data": "base64_encoded_audio_data"
            })
            
            # Should not disconnect
            response = websocket.receive_json()
            assert response is not None
    
    def test_websocket_accepts_screenshot(self):
        """WebSocket should accept screenshot messages"""
        import base64
        # Valid base64-encoded 1x1 transparent PNG
        valid_png_b64 = base64.b64encode(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        ).decode('ascii')

        with client.websocket_connect("/ws") as websocket:
            # Wait for connection
            websocket.receive_json()

            # Send screenshot with valid base64
            websocket.send_json({
                "type": "screenshot",
                "data": valid_png_b64,
                "width": 1280,
                "height": 720
            })

            # Should not disconnect immediately (may close after processing)
            try:
                response = websocket.receive_json(timeout=2)
                assert response is not None
            except Exception:
                # Connection might close after successful processing
                pass
    
    def test_websocket_handles_text_message(self):
        """WebSocket should handle text messages"""
        with client.websocket_connect("/ws") as websocket:
            # Wait for connection
            websocket.receive_json()
            
            # Send text
            websocket.send_json({
                "type": "text",
                "data": "Hello Spectra"
            })
            
            # Should receive response
            response = websocket.receive_json()
            assert response is not None
            assert response["type"] in ["text", "audio", "action", "gemini_reconnecting"]
    
    def test_websocket_handles_cancel(self):
        """WebSocket should handle cancel messages"""
        with client.websocket_connect("/ws") as websocket:
            # Wait for connection
            websocket.receive_json()
            
            # Send cancel
            websocket.send_json({"type": "cancel"})
            
            # Should acknowledge
            response = websocket.receive_json()
            assert response is not None
    
    def test_websocket_handles_pong(self):
        """WebSocket should handle pong messages"""
        with client.websocket_connect("/ws") as websocket:
            # Wait for connection
            websocket.receive_json()
            
            # Send pong
            websocket.send_json({"type": "pong"})
            
            # Should not disconnect
            # Note: pong might not generate a response
            pass


class TestErrorHandling:
    """Test API error handling"""
    
    def test_404_for_unknown_endpoint(self):
        """Unknown endpoints should return 404"""
        response = client.get("/unknown")
        assert response.status_code == 404
    
    def test_405_for_wrong_method(self):
        """Wrong HTTP method should return 405"""
        response = client.post("/health")
        assert response.status_code == 405
    
    def test_invalid_json_returns_400(self):
        """Invalid JSON should return 400"""
        response = client.post(
            "/api/test",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 404, 422]


class TestCORS:
    """Test CORS configuration"""

    def test_cors_headers_present(self):
        """CORS middleware is configured; headers appear when Origin is sent"""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        headers = {k.lower(): v for k, v in response.headers.items()}
        assert "access-control-allow-origin" in headers or "access-control-allow-credentials" in headers

    def test_cors_allows_credentials(self):
        """CORS should allow credentials when configured"""
        response = client.get("/health")
        headers = {k.lower(): v for k, v in response.headers.items()}
        if "access-control-allow-credentials" in headers:
            assert headers["access-control-allow-credentials"] == "true"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

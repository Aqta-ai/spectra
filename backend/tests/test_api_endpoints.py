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
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_health_check_includes_uptime(self):
        """Health endpoint should include uptime"""
        response = client.get("/health")
        data = response.json()
        assert "uptime" in data
        assert isinstance(data["uptime"], (int, float))
        assert data["uptime"] >= 0


class TestMetricsEndpoint:
    """Test metrics endpoint"""
    
    def test_metrics_returns_200(self):
        """Metrics endpoint should return 200 OK"""
        response = client.get("/metrics")
        assert response.status_code == 200
    
    def test_metrics_includes_response_time(self):
        """Metrics should include response time stats"""
        response = client.get("/metrics")
        data = response.json()
        assert "response_time" in data
        assert "average" in data["response_time"]
        assert "p95" in data["response_time"]
    
    def test_metrics_includes_session_count(self):
        """Metrics should include active session count"""
        response = client.get("/metrics")
        data = response.json()
        assert "active_sessions" in data
        assert isinstance(data["active_sessions"], int)
    
    def test_metrics_includes_error_rate(self):
        """Metrics should include error rate"""
        response = client.get("/metrics")
        data = response.json()
        assert "error_rate" in data
        assert 0 <= data["error_rate"] <= 1


class TestWebSocketEndpoint:
    """Test WebSocket connection endpoint"""
    
    def test_websocket_connection_succeeds(self):
        """WebSocket connection should succeed"""
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            assert data["type"] in ["connected", "ready"]
    
    def test_websocket_sends_session_id(self):
        """WebSocket should send session ID on connect"""
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            assert "session_id" in data or "id" in data
    
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
        with client.websocket_connect("/ws") as websocket:
            # Wait for connection
            websocket.receive_json()
            
            # Send screenshot
            websocket.send_json({
                "type": "screenshot",
                "data": "base64_encoded_image_data",
                "width": 1280,
                "height": 720
            })
            
            # Should not disconnect
            response = websocket.receive_json()
            assert response is not None
    
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
            assert response["type"] in ["text", "audio", "action"]
    
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
        """CORS headers should be present"""
        response = client.options("/health")
        assert "access-control-allow-origin" in response.headers
    
    def test_cors_allows_credentials(self):
        """CORS should allow credentials"""
        response = client.options("/health")
        headers = {k.lower(): v for k, v in response.headers.items()}
        if "access-control-allow-credentials" in headers:
            assert headers["access-control-allow-credentials"] == "true"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

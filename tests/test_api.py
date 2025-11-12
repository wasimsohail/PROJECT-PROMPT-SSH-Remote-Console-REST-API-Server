"""
API endpoint tests for SSH Console API Server
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from config import config

# Test client
client = TestClient(app)

# Test API key
TEST_API_KEY = config.api_key


class TestHealthEndpoints:
    """Test health and utility endpoints"""

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "active_sessions" in data
        assert "uptime_seconds" in data

    def test_version_info(self):
        """Test version endpoint"""
        response = client.get("/api/v1/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "build_date" in data
        assert "python_version" in data

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "version" in data


class TestAuthentication:
    """Test authentication and security"""

    def test_missing_api_key(self):
        """Test request without API key"""
        response = client.get("/api/v1/sessions")
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "MISSING_API_KEY"

    def test_invalid_api_key(self):
        """Test request with invalid API key"""
        response = client.get(
            "/api/v1/sessions",
            headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "INVALID_API_KEY"

    def test_valid_api_key(self):
        """Test request with valid API key"""
        response = client.get(
            "/api/v1/sessions",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200


class TestSessionEndpoints:
    """Test session management endpoints"""

    def test_list_sessions_empty(self):
        """Test listing sessions when none exist"""
        response = client.get(
            "/api/v1/sessions",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total_count" in data
        assert isinstance(data["sessions"], list)

    def test_create_session_invalid_host(self):
        """Test creating session with invalid host"""
        response = client.post(
            "/api/v1/sessions",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "host": "invalid-host-that-does-not-exist",
                "port": 22,
                "username": "test",
                "password": "test",
                "auth_type": "password"
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_get_nonexistent_session(self):
        """Test getting a session that doesn't exist"""
        response = client.get(
            "/api/v1/sessions/nonexistent-id",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "SESSION_NOT_FOUND"

    def test_delete_nonexistent_session(self):
        """Test deleting a session that doesn't exist"""
        response = client.delete(
            "/api/v1/sessions/nonexistent-id",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 404


class TestCommandEndpoints:
    """Test command execution endpoints"""

    def test_execute_command_nonexistent_session(self):
        """Test executing command on nonexistent session"""
        response = client.post(
            "/api/v1/sessions/nonexistent-id/execute",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "command": "ls -la",
                "timeout": 30
            }
        )
        assert response.status_code in [400, 404]

    def test_get_output_nonexistent_session(self):
        """Test getting output from nonexistent session"""
        response = client.get(
            "/api/v1/sessions/nonexistent-id/output",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 404

    def test_get_history_nonexistent_session(self):
        """Test getting command history from nonexistent session"""
        response = client.get(
            "/api/v1/sessions/nonexistent-id/commands",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code in [404, 500]


class TestConnectionTest:
    """Test connection testing endpoint"""

    def test_connection_test_invalid_host(self):
        """Test connection test with invalid host"""
        response = client.post(
            "/api/v1/test-connection",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "host": "invalid-host-12345",
                "port": 22,
                "username": "test",
                "password": "test",
                "auth_type": "password",
                "timeout": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is False
        assert "message" in data


class TestInputValidation:
    """Test input validation"""

    def test_invalid_port_number(self):
        """Test with invalid port number"""
        response = client.post(
            "/api/v1/sessions",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "host": "localhost",
                "port": 99999,  # Invalid port
                "username": "test",
                "password": "test"
            }
        )
        assert response.status_code == 422  # Validation error

    def test_missing_required_fields(self):
        """Test with missing required fields"""
        response = client.post(
            "/api/v1/sessions",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "host": "localhost"
                # Missing username, password, etc.
            }
        )
        assert response.status_code == 422

    def test_invalid_auth_type(self):
        """Test with invalid auth type"""
        response = client.post(
            "/api/v1/sessions",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "host": "localhost",
                "port": 22,
                "username": "test",
                "password": "test",
                "auth_type": "invalid"  # Invalid auth type
            }
        )
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

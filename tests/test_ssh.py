"""
SSH Manager tests
"""
import pytest
from models import CreateSessionRequest, AuthType
from ssh_manager import SSHManager


class TestSSHManager:
    """Test SSH manager functionality"""

    @pytest.fixture
    def ssh_manager(self):
        """Create SSH manager instance"""
        return SSHManager()

    def test_ssh_manager_initialization(self, ssh_manager):
        """Test SSH manager initializes correctly"""
        assert ssh_manager is not None
        assert len(ssh_manager.sessions) == 0

    @pytest.mark.asyncio
    async def test_list_empty_sessions(self, ssh_manager):
        """Test listing sessions when none exist"""
        sessions = await ssh_manager.list_sessions()
        assert isinstance(sessions, list)
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, ssh_manager):
        """Test getting a session that doesn't exist"""
        session = await ssh_manager.get_session("nonexistent-id")
        assert session is None

    @pytest.mark.asyncio
    async def test_close_nonexistent_session(self, ssh_manager):
        """Test closing a session that doesn't exist"""
        result = await ssh_manager.close_session("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_connection_test_invalid_host(self, ssh_manager):
        """Test connection to invalid host"""
        request = CreateSessionRequest(
            host="invalid-host-12345.example.com",
            port=22,
            username="test",
            password="test",
            auth_type=AuthType.PASSWORD,
            timeout=5
        )

        success, message, response_time = await ssh_manager.test_connection(request)
        assert success is False
        assert "failed" in message.lower()
        assert response_time >= 0

    @pytest.mark.asyncio
    async def test_create_session_invalid_host(self, ssh_manager):
        """Test creating session with invalid host"""
        request = CreateSessionRequest(
            host="invalid-host-12345.example.com",
            port=22,
            username="test",
            password="test",
            auth_type=AuthType.PASSWORD,
            timeout=5
        )

        with pytest.raises(Exception):
            await ssh_manager.create_session(request)

    @pytest.mark.asyncio
    async def test_execute_command_nonexistent_session(self, ssh_manager):
        """Test executing command on nonexistent session"""
        with pytest.raises(Exception) as excinfo:
            await ssh_manager.execute_command("nonexistent-id", "ls", 30)

        assert "not found" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_get_output_nonexistent_session(self, ssh_manager):
        """Test getting output from nonexistent session"""
        with pytest.raises(Exception) as excinfo:
            await ssh_manager.get_output("nonexistent-id")

        assert "not found" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_get_history_nonexistent_session(self, ssh_manager):
        """Test getting command history from nonexistent session"""
        with pytest.raises(Exception) as excinfo:
            await ssh_manager.get_command_history("nonexistent-id")

        assert "not found" in str(excinfo.value).lower()


class TestModels:
    """Test Pydantic models"""

    def test_create_session_request_valid(self):
        """Test valid session creation request"""
        request = CreateSessionRequest(
            host="localhost",
            port=22,
            username="test",
            password="test123",
            auth_type=AuthType.PASSWORD
        )

        assert request.host == "localhost"
        assert request.port == 22
        assert request.username == "test"
        assert request.password == "test123"
        assert request.auth_type == AuthType.PASSWORD

    def test_create_session_request_defaults(self):
        """Test session request with default values"""
        request = CreateSessionRequest(
            host="localhost",
            username="test",
            password="test123"
        )

        assert request.port == 22  # Default port
        assert request.timeout == 30  # Default timeout
        assert request.auth_type == AuthType.PASSWORD  # Default auth type

    def test_create_session_request_with_label(self):
        """Test session request with label"""
        request = CreateSessionRequest(
            host="localhost",
            username="test",
            password="test123",
            label="My Server"
        )

        assert request.label == "My Server"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

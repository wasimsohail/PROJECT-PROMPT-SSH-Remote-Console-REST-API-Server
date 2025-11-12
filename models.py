"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AuthType(str, Enum):
    """Authentication type enumeration"""
    PASSWORD = "password"
    KEY = "key"


class SessionStatus(str, Enum):
    """Session status enumeration"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CONNECTING = "connecting"


class CommandStatus(str, Enum):
    """Command execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# Request Models
class CreateSessionRequest(BaseModel):
    """Request model for creating a new SSH session"""
    host: str = Field(..., description="SSH host address")
    port: int = Field(22, description="SSH port", ge=1, le=65535)
    username: str = Field(..., description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")
    private_key: Optional[str] = Field(None, description="SSH private key content")
    private_key_path: Optional[str] = Field(None, description="Path to SSH private key file")
    auth_type: AuthType = Field(AuthType.PASSWORD, description="Authentication type")
    timeout: int = Field(30, description="Connection timeout in seconds", ge=1, le=300)
    label: Optional[str] = Field(None, description="Custom label for the session")

    @field_validator('password', 'private_key', 'private_key_path', mode='after')
    @classmethod
    def validate_auth(cls, v, info):
        """Ensure proper authentication credentials are provided"""
        return v

    def model_post_init(self, __context):
        """Validate authentication credentials match auth_type"""
        if self.auth_type == AuthType.PASSWORD:
            if not self.password:
                raise ValueError("Password is required when auth_type is 'password'")
        elif self.auth_type == AuthType.KEY:
            if not self.private_key and not self.private_key_path:
                raise ValueError("Either private_key or private_key_path is required when auth_type is 'key'")


class ExecuteCommandRequest(BaseModel):
    """Request model for executing a command"""
    command: str = Field(..., description="Command to execute")
    timeout: int = Field(30, description="Command timeout in seconds", ge=1, le=300)
    wait_for_output: bool = Field(True, description="Wait for command output")


class ShellExecuteRequest(BaseModel):
    """Request model for shell command execution"""
    command: str = Field(..., description="Shell command to execute")
    timeout: int = Field(30, description="Command timeout in seconds", ge=1, le=300)


class TestConnectionRequest(BaseModel):
    """Request model for testing SSH connection"""
    host: str = Field(..., description="SSH host address")
    port: int = Field(22, description="SSH port", ge=1, le=65535)
    username: str = Field(..., description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")
    private_key: Optional[str] = Field(None, description="SSH private key content")
    auth_type: AuthType = Field(AuthType.PASSWORD, description="Authentication type")
    timeout: int = Field(10, description="Connection timeout in seconds", ge=1, le=60)


# Response Models
class SessionResponse(BaseModel):
    """Response model for session information"""
    session_id: str = Field(..., description="Unique session identifier")
    status: SessionStatus = Field(..., description="Session connection status")
    created_at: datetime = Field(..., description="Session creation timestamp")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    host: str = Field(..., description="SSH host address")
    port: int = Field(..., description="SSH port")
    username: str = Field(..., description="SSH username")
    label: Optional[str] = Field(None, description="Custom session label")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CommandResponse(BaseModel):
    """Response model for command execution"""
    command_id: str = Field(..., description="Unique command identifier")
    command: str = Field(..., description="Executed command")
    status: CommandStatus = Field(..., description="Command execution status")
    output: str = Field("", description="Command output")
    error: str = Field("", description="Error output")
    exit_code: Optional[int] = Field(None, description="Command exit code")
    execution_time: float = Field(..., description="Execution time in seconds")
    timestamp: datetime = Field(..., description="Command execution timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionListResponse(BaseModel):
    """Response model for listing sessions"""
    sessions: List[SessionResponse] = Field(..., description="List of active sessions")
    total_count: int = Field(..., description="Total number of sessions")


class CommandHistoryResponse(BaseModel):
    """Response model for command history"""
    commands: List[CommandResponse] = Field(..., description="List of executed commands")
    total_count: int = Field(..., description="Total number of commands")


class OutputResponse(BaseModel):
    """Response model for session output"""
    session_id: str = Field(..., description="Session identifier")
    output: str = Field(..., description="Buffered output")
    timestamp: datetime = Field(..., description="Output timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Server status")
    active_sessions: int = Field(..., description="Number of active sessions")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    timestamp: datetime = Field(..., description="Health check timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class VersionResponse(BaseModel):
    """Response model for version information"""
    version: str = Field(..., description="API version")
    build_date: str = Field(..., description="Build date")
    python_version: str = Field(..., description="Python version")


class TestConnectionResponse(BaseModel):
    """Response model for connection test"""
    success: bool = Field(..., description="Connection test result")
    message: str = Field(..., description="Connection test message")
    response_time: float = Field(..., description="Connection response time in seconds")
    timestamp: datetime = Field(..., description="Test timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorDetail(BaseModel):
    """Error detail model"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: ErrorDetail = Field(..., description="Error information")

"""
SSH Remote Console REST API Server
Main FastAPI application
"""
import sys
import platform
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from models import (
    CreateSessionRequest, ExecuteCommandRequest, ShellExecuteRequest,
    TestConnectionRequest, SessionResponse, CommandResponse,
    SessionListResponse, CommandHistoryResponse, OutputResponse,
    HealthResponse, VersionResponse, TestConnectionResponse, ErrorResponse
)
from security import verify_api_key, get_rate_limit_info
from ssh_manager import ssh_manager
from config import config
from logger import get_logger

logger = get_logger(__name__)

# Application version
VERSION = "1.0.0"
BUILD_DATE = "2025-11-12"

# Store startup time for uptime calculation
startup_time = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("=" * 60)
    logger.info("SSH Remote Console REST API Server")
    logger.info(f"Version: {VERSION}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Platform: {platform.system()} {platform.release()}")
    logger.info("=" * 60)
    logger.info(f"Server starting on {config.server_host}:{config.server_port}")
    logger.info(f"Max sessions: {config.max_sessions}")
    logger.info(f"Idle timeout: {config.idle_timeout}s")
    logger.info(f"API docs: http://{config.server_host}:{config.server_port}/docs")
    logger.info("=" * 60)

    # Start cleanup task
    await ssh_manager.start_cleanup_task()

    yield

    # Shutdown
    logger.info("Shutting down server...")
    await ssh_manager.stop_cleanup_task()
    await ssh_manager.close_all_sessions()
    logger.info("Server shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="SSH Remote Console REST API",
    description="REST API for managing SSH connections and executing remote commands",
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware (only if enabled for security reasons)
if config.cors_enabled and config.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["X-API-Key", "Content-Type"],
    )
    logger.info(f"CORS enabled for origins: {config.cors_origins}")


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
                "details": {},
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


# Middleware for rate limit headers
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    """Add rate limit headers to response"""
    response = await call_next(request)

    # Add rate limit headers if enabled
    rate_info = get_rate_limit_info(request)
    for header, value in rate_info.items():
        response.headers[header] = value

    return response


# ============================================================================
# Session Management Endpoints
# ============================================================================

@app.post(
    "/api/v1/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Sessions"],
    summary="Create new SSH session"
)
async def create_session(
    request: CreateSessionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Create a new SSH session with the specified connection parameters.

    - **host**: SSH server hostname or IP address
    - **port**: SSH server port (default: 22)
    - **username**: SSH username
    - **password**: SSH password (for password auth)
    - **private_key**: SSH private key content (for key auth)
    - **private_key_path**: Path to SSH private key file (for key auth)
    - **auth_type**: Authentication type (password or key)
    - **timeout**: Connection timeout in seconds
    - **label**: Optional custom label for the session
    """
    try:
        session = await ssh_manager.create_session(request)
        return session
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "SESSION_CREATE_FAILED",
                    "message": str(e),
                    "details": {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


@app.get(
    "/api/v1/sessions",
    response_model=SessionListResponse,
    tags=["Sessions"],
    summary="List all active sessions"
)
async def list_sessions(api_key: str = Depends(verify_api_key)):
    """
    Get a list of all active SSH sessions.
    """
    try:
        sessions = await ssh_manager.list_sessions()
        return SessionListResponse(
            sessions=sessions,
            total_count=len(sessions)
        )
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "LIST_SESSIONS_FAILED",
                    "message": str(e),
                    "details": {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


@app.get(
    "/api/v1/sessions/{session_id}",
    response_model=SessionResponse,
    tags=["Sessions"],
    summary="Get session details"
)
async def get_session(
    session_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get detailed information about a specific session.
    """
    try:
        session = await ssh_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "SESSION_NOT_FOUND",
                        "message": f"Session {session_id} not found",
                        "details": {},
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "GET_SESSION_FAILED",
                    "message": str(e),
                    "details": {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


@app.delete(
    "/api/v1/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Sessions"],
    summary="Close and remove session"
)
async def delete_session(
    session_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Close an SSH session and remove it from the active sessions list.
    """
    try:
        success = await ssh_manager.close_session(session_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "SESSION_NOT_FOUND",
                        "message": f"Session {session_id} not found",
                        "details": {},
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DELETE_SESSION_FAILED",
                    "message": str(e),
                    "details": {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


# ============================================================================
# Command Execution Endpoints
# ============================================================================

@app.post(
    "/api/v1/sessions/{session_id}/execute",
    response_model=CommandResponse,
    tags=["Commands"],
    summary="Execute command on session"
)
async def execute_command(
    session_id: str,
    request: ExecuteCommandRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Execute a command on an existing SSH session.

    - **command**: The command to execute
    - **timeout**: Maximum time to wait for command completion (seconds)
    - **wait_for_output**: Whether to wait for command output
    """
    try:
        result = await ssh_manager.execute_command(
            session_id,
            request.command,
            request.timeout
        )
        return result
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        if "not found" in str(e).lower():
            status_code = status.HTTP_404_NOT_FOUND
            error_code = "SESSION_NOT_FOUND"
        elif "timeout" in str(e).lower():
            status_code = status.HTTP_408_REQUEST_TIMEOUT
            error_code = "COMMAND_TIMEOUT"
        else:
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = "COMMAND_EXECUTION_FAILED"

        raise HTTPException(
            status_code=status_code,
            detail={
                "error": {
                    "code": error_code,
                    "message": str(e),
                    "details": {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


@app.post(
    "/api/v1/sessions/{session_id}/shell/execute",
    response_model=CommandResponse,
    tags=["Commands"],
    summary="Execute command in shell mode"
)
async def shell_execute(
    session_id: str,
    request: ShellExecuteRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Execute a command in interactive shell mode.
    This maintains shell state between commands.
    """
    # For now, use same implementation as execute_command
    # In a full implementation, this would use a persistent shell channel
    try:
        result = await ssh_manager.execute_command(
            session_id,
            request.command,
            request.timeout
        )
        return result
    except Exception as e:
        logger.error(f"Shell command execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "SHELL_EXECUTION_FAILED",
                    "message": str(e),
                    "details": {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


@app.get(
    "/api/v1/sessions/{session_id}/output",
    response_model=OutputResponse,
    tags=["Commands"],
    summary="Get buffered output"
)
async def get_output(
    session_id: str,
    clear: bool = False,
    api_key: str = Depends(verify_api_key)
):
    """
    Get buffered output from a session.

    - **clear**: If true, clear the buffer after reading
    """
    try:
        output, timestamp = await ssh_manager.get_output(session_id, clear)
        return OutputResponse(
            session_id=session_id,
            output=output,
            timestamp=timestamp
        )
    except Exception as e:
        logger.error(f"Failed to get output: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "GET_OUTPUT_FAILED",
                    "message": str(e),
                    "details": {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


@app.get(
    "/api/v1/sessions/{session_id}/commands",
    response_model=CommandHistoryResponse,
    tags=["Commands"],
    summary="Get command history"
)
async def get_command_history(
    session_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get the command execution history for a session.
    """
    try:
        commands = await ssh_manager.get_command_history(session_id)
        return CommandHistoryResponse(
            commands=commands,
            total_count=len(commands)
        )
    except Exception as e:
        logger.error(f"Failed to get command history: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "GET_HISTORY_FAILED",
                    "message": str(e),
                    "details": {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


# ============================================================================
# Utility Endpoints
# ============================================================================

@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    tags=["Utility"],
    summary="Health check"
)
async def health_check():
    """
    Health check endpoint.
    Returns server status and active session count.
    """
    uptime = (datetime.utcnow() - startup_time).total_seconds()
    sessions = await ssh_manager.list_sessions()

    return HealthResponse(
        status="healthy",
        active_sessions=len(sessions),
        uptime_seconds=uptime,
        timestamp=datetime.utcnow()
    )


@app.get(
    "/api/v1/version",
    response_model=VersionResponse,
    tags=["Utility"],
    summary="Get version info"
)
async def get_version():
    """
    Get API version and build information.
    """
    return VersionResponse(
        version=VERSION,
        build_date=BUILD_DATE,
        python_version=sys.version.split()[0]
    )


@app.post(
    "/api/v1/test-connection",
    response_model=TestConnectionResponse,
    tags=["Utility"],
    summary="Test SSH connection"
)
async def test_connection(
    request: TestConnectionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Test SSH connectivity without creating a session.
    Useful for validating credentials and network connectivity.
    """
    try:
        # Convert to CreateSessionRequest
        create_request = CreateSessionRequest(
            host=request.host,
            port=request.port,
            username=request.username,
            password=request.password,
            private_key=request.private_key,
            auth_type=request.auth_type,
            timeout=request.timeout
        )

        success, message, response_time = await ssh_manager.test_connection(create_request)

        return TestConnectionResponse(
            success=success,
            message=message,
            response_time=response_time,
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return TestConnectionResponse(
            success=False,
            message=f"Connection test failed: {str(e)}",
            response_time=0.0,
            timestamp=datetime.utcnow()
        )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "SSH Remote Console REST API",
        "version": VERSION,
        "status": "running",
        "documentation": "/docs",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.server_host,
        port=config.server_port,
        reload=config.reload,
        log_level=config.log_level.lower()
    )

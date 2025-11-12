"""
SSH session manager for handling SSH connections and command execution
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from threading import Lock
import paramiko
import io
import time

from models import (
    SessionStatus, CommandStatus, CreateSessionRequest,
    SessionResponse, CommandResponse, AuthType
)
from config import config
from logger import get_logger, get_audit_logger

logger = get_logger(__name__)
audit_logger = get_audit_logger()


@dataclass
class CommandRecord:
    """Record of executed command"""
    command_id: str
    command: str
    output: str = ""
    error: str = ""
    exit_code: Optional[int] = None
    status: CommandStatus = CommandStatus.PENDING
    timestamp: datetime = field(default_factory=datetime.utcnow)
    execution_time: float = 0.0


@dataclass
class SSHSession:
    """SSH session data"""
    session_id: str
    host: str
    port: int
    username: str
    label: Optional[str]
    client: paramiko.SSHClient
    status: SessionStatus = SessionStatus.CONNECTING
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    output_buffer: str = ""
    command_history: List[CommandRecord] = field(default_factory=list)
    shell_channel: Optional[paramiko.Channel] = None


class SSHManager:
    """Manager for SSH sessions"""

    def __init__(self):
        """Initialize SSH manager"""
        self.sessions: Dict[str, SSHSession] = {}
        self.lock = Lock()
        self._cleanup_task = None

    async def start_cleanup_task(self):
        """Start background task for cleaning up idle sessions"""
        self._cleanup_task = asyncio.create_task(self._cleanup_idle_sessions())

    async def stop_cleanup_task(self):
        """Stop cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_idle_sessions(self):
        """Background task to cleanup idle sessions"""
        while True:
            try:
                await asyncio.sleep(config.cleanup_interval)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    async def _cleanup_expired_sessions(self):
        """Remove sessions that have exceeded idle timeout"""
        now = datetime.utcnow()
        expired_sessions = []

        with self.lock:
            for session_id, session in self.sessions.items():
                idle_time = (now - session.last_activity).total_seconds()
                if idle_time > config.idle_timeout:
                    expired_sessions.append(session_id)

        for session_id in expired_sessions:
            logger.info(f"Closing idle session: {session_id}")
            await self.close_session(session_id, reason="idle_timeout")

    def _create_ssh_client(self, request: CreateSessionRequest) -> paramiko.SSHClient:
        """
        Create and configure SSH client

        Args:
            request: Session creation request

        Returns:
            Configured SSH client

        Raises:
            Exception: If connection fails
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # Prepare authentication
            connect_kwargs = {
                'hostname': request.host,
                'port': request.port,
                'username': request.username,
                'timeout': request.timeout,
                'allow_agent': False,
                'look_for_keys': False
            }

            # Add authentication credentials
            if request.auth_type == AuthType.PASSWORD:
                if not request.password:
                    raise ValueError("Password is required for password authentication")
                connect_kwargs['password'] = request.password
            elif request.auth_type == AuthType.KEY:
                if request.private_key:
                    # Load private key from string
                    key_file = io.StringIO(request.private_key)
                    try:
                        pkey = paramiko.RSAKey.from_private_key(key_file)
                    except:
                        key_file.seek(0)
                        try:
                            pkey = paramiko.Ed25519Key.from_private_key(key_file)
                        except:
                            key_file.seek(0)
                            pkey = paramiko.ECDSAKey.from_private_key(key_file)
                    connect_kwargs['pkey'] = pkey
                elif request.private_key_path:
                    connect_kwargs['key_filename'] = request.private_key_path
                else:
                    raise ValueError("Private key or key path is required for key authentication")

            # Connect
            client.connect(**connect_kwargs)
            logger.info(f"SSH connection established to {request.host}:{request.port}")

            return client

        except Exception as e:
            logger.error(f"Failed to connect to {request.host}:{request.port} - {e}")
            client.close()
            raise

    async def create_session(self, request: CreateSessionRequest) -> SessionResponse:
        """
        Create new SSH session

        Args:
            request: Session creation request

        Returns:
            Session response with session details

        Raises:
            Exception: If session limit reached or connection fails
        """
        # Check session limit
        with self.lock:
            if len(self.sessions) >= config.max_sessions:
                raise Exception(f"Maximum session limit ({config.max_sessions}) reached")

        session_id = str(uuid.uuid4())

        try:
            # Create SSH client in thread pool (blocking operation)
            loop = asyncio.get_event_loop()
            client = await loop.run_in_executor(None, self._create_ssh_client, request)

            # Create session object
            session = SSHSession(
                session_id=session_id,
                host=request.host,
                port=request.port,
                username=request.username,
                label=request.label,
                client=client,
                status=SessionStatus.CONNECTED
            )

            # Store session
            with self.lock:
                self.sessions[session_id] = session

            # Log session creation
            if audit_logger:
                audit_logger.log_session_create(session_id, request.host, request.username, request.label)

            logger.info(f"Session created: {session_id} for {request.host}")

            return SessionResponse(
                session_id=session.session_id,
                status=session.status,
                created_at=session.created_at,
                last_activity=session.last_activity,
                host=session.host,
                port=session.port,
                username=session.username,
                label=session.label
            )

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise Exception(f"Failed to create SSH session: {str(e)}")

    def _execute_command_blocking(self, client: paramiko.SSHClient, command: str, timeout: int) -> Tuple[str, str, int]:
        """
        Execute command synchronously (blocking)

        Args:
            client: SSH client
            command: Command to execute
            timeout: Timeout in seconds

        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)

        # Read output
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        exit_code = stdout.channel.recv_exit_status()

        return output, error, exit_code

    async def execute_command(self, session_id: str, command: str, timeout: int = 30) -> CommandResponse:
        """
        Execute command on SSH session

        Args:
            session_id: Session identifier
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            Command execution response

        Raises:
            Exception: If session not found or execution fails
        """
        # Get session
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                raise Exception(f"Session {session_id} not found")
            if session.status != SessionStatus.CONNECTED:
                raise Exception(f"Session {session_id} is not connected")

        command_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            # Execute command in thread pool (blocking operation)
            loop = asyncio.get_event_loop()
            output, error, exit_code = await loop.run_in_executor(
                None,
                self._execute_command_blocking,
                session.client,
                command,
                timeout
            )

            execution_time = time.time() - start_time

            # Create command record
            command_record = CommandRecord(
                command_id=command_id,
                command=command,
                output=output,
                error=error,
                exit_code=exit_code,
                status=CommandStatus.COMPLETED,
                execution_time=execution_time
            )

            # Update session
            with self.lock:
                session.last_activity = datetime.utcnow()
                session.output_buffer += output + error
                session.command_history.append(command_record)

            # Log command execution
            if audit_logger:
                audit_logger.log_command(
                    session_id, session.host, session.username,
                    command, exit_code, error
                )

            logger.info(f"Command executed on session {session_id}: {command[:50]}...")

            return CommandResponse(
                command_id=command_record.command_id,
                command=command_record.command,
                status=command_record.status,
                output=command_record.output,
                error=command_record.error,
                exit_code=command_record.exit_code,
                execution_time=command_record.execution_time,
                timestamp=command_record.timestamp
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Command execution failed on session {session_id}: {e}")

            command_record = CommandRecord(
                command_id=command_id,
                command=command,
                error=str(e),
                status=CommandStatus.FAILED,
                execution_time=execution_time
            )

            with self.lock:
                session.command_history.append(command_record)

            raise Exception(f"Command execution failed: {str(e)}")

    async def get_session(self, session_id: str) -> Optional[SessionResponse]:
        """
        Get session details

        Args:
            session_id: Session identifier

        Returns:
            Session response or None if not found
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                return None

            return SessionResponse(
                session_id=session.session_id,
                status=session.status,
                created_at=session.created_at,
                last_activity=session.last_activity,
                host=session.host,
                port=session.port,
                username=session.username,
                label=session.label
            )

    async def list_sessions(self) -> List[SessionResponse]:
        """
        List all active sessions

        Returns:
            List of session responses
        """
        with self.lock:
            return [
                SessionResponse(
                    session_id=session.session_id,
                    status=session.status,
                    created_at=session.created_at,
                    last_activity=session.last_activity,
                    host=session.host,
                    port=session.port,
                    username=session.username,
                    label=session.label
                )
                for session in self.sessions.values()
            ]

    async def close_session(self, session_id: str, reason: str = "normal") -> bool:
        """
        Close SSH session

        Args:
            session_id: Session identifier
            reason: Reason for closing

        Returns:
            True if closed successfully, False if session not found
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                return False

            try:
                # Close shell channel if exists
                if session.shell_channel:
                    session.shell_channel.close()

                # Close SSH client
                session.client.close()
                session.status = SessionStatus.DISCONNECTED

                # Log session closure
                if audit_logger:
                    audit_logger.log_session_close(session_id, session.host, reason)

                # Remove from sessions
                del self.sessions[session_id]

                logger.info(f"Session {session_id} closed: {reason}")
                return True

            except Exception as e:
                logger.error(f"Error closing session {session_id}: {e}")
                return False

    async def get_output(self, session_id: str, clear: bool = False) -> Tuple[str, datetime]:
        """
        Get buffered output from session

        Args:
            session_id: Session identifier
            clear: Whether to clear buffer after reading

        Returns:
            Tuple of (output, timestamp)

        Raises:
            Exception: If session not found
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                raise Exception(f"Session {session_id} not found")

            output = session.output_buffer
            timestamp = session.last_activity

            if clear:
                session.output_buffer = ""

            session.last_activity = datetime.utcnow()

            return output, timestamp

    async def get_command_history(self, session_id: str) -> List[CommandResponse]:
        """
        Get command history for session

        Args:
            session_id: Session identifier

        Returns:
            List of command responses

        Raises:
            Exception: If session not found
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                raise Exception(f"Session {session_id} not found")

            return [
                CommandResponse(
                    command_id=cmd.command_id,
                    command=cmd.command,
                    status=cmd.status,
                    output=cmd.output,
                    error=cmd.error,
                    exit_code=cmd.exit_code,
                    execution_time=cmd.execution_time,
                    timestamp=cmd.timestamp
                )
                for cmd in session.command_history
            ]

    async def test_connection(self, request: CreateSessionRequest) -> Tuple[bool, str, float]:
        """
        Test SSH connection without creating session

        Args:
            request: Connection test request

        Returns:
            Tuple of (success, message, response_time)
        """
        start_time = time.time()

        try:
            loop = asyncio.get_event_loop()
            client = await loop.run_in_executor(None, self._create_ssh_client, request)
            client.close()

            response_time = time.time() - start_time
            return True, "Connection successful", response_time

        except Exception as e:
            response_time = time.time() - start_time
            return False, f"Connection failed: {str(e)}", response_time

    async def close_all_sessions(self):
        """Close all active sessions"""
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id, reason="shutdown")


# Global SSH manager instance
ssh_manager = SSHManager()

# SSH Remote Console REST API Server

A standalone, cross-platform (Windows/Linux) Python application that provides a REST API interface for managing SSH connections and executing commands on remote systems. This is a pure API server with no GUI - all interactions happen through HTTP REST endpoints.

## Features

- **Multi-OS Support**: Works on Windows and Linux
- **REST API Interface**: Complete HTTP API for SSH operations
- **Session Management**: Create and manage multiple concurrent SSH sessions
- **Command Execution**: Execute commands on remote systems via SSH
- **Authentication**: API key-based authentication for security
- **Rate Limiting**: Built-in rate limiting to prevent abuse
- **IP Whitelisting**: Optional IP-based access control
- **Audit Logging**: Comprehensive logging of all commands and security events
- **Auto-cleanup**: Automatic cleanup of idle sessions
- **Interactive Documentation**: Auto-generated Swagger UI documentation

## Quick Start

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd PROJECT-PROMPT-SSH-Remote-Console-REST-API-Server
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the application**:
   - Edit `config.ini` to set your API key and other settings
   - **IMPORTANT**: Change the default API key before running in production!

4. **Run the server**:
   ```bash
   python main.py
   ```

The server will start on `http://0.0.0.0:8000` by default.

### First API Call

Access the interactive API documentation at `http://localhost:8000/docs`

Example health check:
```bash
curl http://localhost:8000/api/v1/health
```

Example session creation:
```bash
curl -X POST "http://localhost:8000/api/v1/sessions" \
  -H "X-API-Key: your-secret-api-key-here-change-this" \
  -H "Content-Type: application/json" \
  -d '{
    "host": "192.168.1.100",
    "port": 22,
    "username": "admin",
    "password": "password123",
    "auth_type": "password",
    "label": "My Server"
  }'
```

## Configuration

The application can be configured via `config.ini` or environment variables.

### Configuration File (config.ini)

```ini
[server]
host = 0.0.0.0
port = 8000
api_key = your-secret-api-key-here-change-this

[sessions]
max_sessions = 50
idle_timeout = 1800
max_command_timeout = 300

[security]
enable_ip_whitelist = false
allowed_ips = 127.0.0.1,192.168.1.0/24
enable_audit_log = true
rate_limit_enabled = true

[logging]
level = INFO
log_file = ssh_api.log
```

### Environment Variables

You can override configuration using environment variables:

- `SERVER_HOST` - Server bind address
- `SERVER_PORT` - Server port
- `API_KEY` - API authentication key
- `MAX_SESSIONS` - Maximum concurrent sessions
- `IDLE_TIMEOUT` - Session idle timeout in seconds
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

## API Endpoints

### Session Management

#### Create Session
```http
POST /api/v1/sessions
```
Create a new SSH session.

**Request Body**:
```json
{
  "host": "192.168.1.1",
  "port": 22,
  "username": "admin",
  "password": "secret",
  "auth_type": "password",
  "timeout": 30,
  "label": "Router-1"
}
```

**Response**:
```json
{
  "session_id": "uuid",
  "status": "connected",
  "created_at": "2025-11-12T10:00:00",
  "last_activity": "2025-11-12T10:00:00",
  "host": "192.168.1.1",
  "port": 22,
  "username": "admin",
  "label": "Router-1"
}
```

#### List Sessions
```http
GET /api/v1/sessions
```
Get all active sessions.

#### Get Session Details
```http
GET /api/v1/sessions/{session_id}
```
Get details of a specific session.

#### Close Session
```http
DELETE /api/v1/sessions/{session_id}
```
Close and remove a session.

### Command Execution

#### Execute Command
```http
POST /api/v1/sessions/{session_id}/execute
```
Execute a command on an SSH session.

**Request Body**:
```json
{
  "command": "ls -la",
  "timeout": 30,
  "wait_for_output": true
}
```

**Response**:
```json
{
  "command_id": "uuid",
  "command": "ls -la",
  "status": "completed",
  "output": "command output here",
  "error": "",
  "exit_code": 0,
  "execution_time": 1.23,
  "timestamp": "2025-11-12T10:00:00"
}
```

#### Get Output Buffer
```http
GET /api/v1/sessions/{session_id}/output?clear=false
```
Get buffered output from a session.

#### Get Command History
```http
GET /api/v1/sessions/{session_id}/commands
```
Get command execution history for a session.

### Utility Endpoints

#### Health Check
```http
GET /api/v1/health
```
Check server health and status.

#### Version Info
```http
GET /api/v1/version
```
Get API version information.

#### Test Connection
```http
POST /api/v1/test-connection
```
Test SSH connectivity without creating a session.

## Authentication

All API endpoints (except `/api/v1/health` and `/api/v1/version`) require authentication using the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/sessions
```

## Security Features

### API Key Authentication
- All requests must include a valid API key
- Configure the API key in `config.ini` or via `API_KEY` environment variable
- **Always change the default API key in production!**

### IP Whitelisting
Enable IP whitelisting to restrict access:

```ini
[security]
enable_ip_whitelist = true
allowed_ips = 127.0.0.1,192.168.1.0/24,10.0.0.0/8
```

### Rate Limiting
Prevent abuse with built-in rate limiting:

```ini
[security]
rate_limit_enabled = true
rate_limit_requests = 100
rate_limit_window = 60
```

### Audit Logging
All commands and security events are logged to `audit.log`:

```ini
[security]
enable_audit_log = true
```

## Building Standalone Executable

### For Windows

1. **Install PyInstaller**:
   ```bash
   pip install pyinstaller
   ```

2. **Build the executable**:
   ```bash
   pyinstaller build.spec
   ```

3. **Find the executable**:
   The built executable will be in `dist/ssh-console-api.exe`

4. **Deploy**:
   - Copy `ssh-console-api.exe` to your target system
   - Create `config.ini` in the same directory
   - Run the executable

### For Linux

The same process works on Linux:

```bash
pyinstaller build.spec
```

The executable will be `dist/ssh-console-api` (no .exe extension).

## Development

### Running in Development Mode

Enable auto-reload for development:

```ini
[server]
reload = true
```

Or run with uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

Run the test suite:

```bash
pytest tests/ -v
```

Run with coverage:

```bash
pytest tests/ --cov=. --cov-report=html
```

### Code Quality

Format code with Black:

```bash
black *.py
```

Check with flake8:

```bash
flake8 *.py
```

Type checking with mypy:

```bash
mypy *.py
```

## Logging

The application generates several log files:

- **ssh_api.log** - Main application log
- **audit.log** - Audit log of commands and security events (if enabled)

Configure logging in `config.ini`:

```ini
[logging]
level = INFO
log_file = ssh_api.log
max_log_size = 10485760
backup_count = 5
```

## Error Handling

All errors follow a standard format:

```json
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "Session with ID xyz not found",
    "details": {},
    "timestamp": "2025-11-12T10:00:00"
  }
}
```

Common error codes:
- `AUTHENTICATION_FAILED` - SSH authentication failed
- `SESSION_NOT_FOUND` - Session doesn't exist
- `CONNECTION_TIMEOUT` - SSH connection timeout
- `COMMAND_TIMEOUT` - Command execution timeout
- `INVALID_API_KEY` - API authentication failed
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `SESSION_LIMIT_REACHED` - Maximum sessions exceeded
- `IP_NOT_ALLOWED` - IP not in whitelist

## Troubleshooting

### Server won't start
- Check if port 8000 is already in use
- Verify config.ini is properly formatted
- Check logs in ssh_api.log

### Can't connect to SSH server
- Verify host/port are correct
- Check network connectivity
- Ensure credentials are valid
- Check SSH server is running

### API key not working
- Ensure X-API-Key header is included
- Verify API key matches config.ini
- Check for typos

### Rate limit errors
- Adjust rate limit settings in config.ini
- Wait for rate limit window to reset
- Increase `rate_limit_requests` if needed

## Project Structure

```
PROJECT-PROMPT-SSH-Remote-Console-REST-API-Server/
├── main.py                 # FastAPI application entry point
├── models.py               # Pydantic models for requests/responses
├── ssh_manager.py          # SSH session management
├── config.py               # Configuration management
├── security.py             # Authentication and security
├── logger.py               # Logging system
├── requirements.txt        # Python dependencies
├── build.spec              # PyInstaller configuration
├── config.ini              # Configuration file
├── tests/                  # Test suite
│   ├── test_api.py
│   └── test_ssh.py
├── examples/               # Example scripts
│   └── client_example.py
└── README.md              # This file
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions, please create an issue in the project repository.

## Version History

### Version 1.0.0 (2025-11-12)
- Initial release
- Core SSH session management
- REST API endpoints
- Authentication and security features
- Audit logging
- Rate limiting
- PyInstaller build support

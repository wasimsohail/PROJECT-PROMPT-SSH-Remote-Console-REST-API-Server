# SSH Console API Server - Deployment Guide

This guide covers building and deploying the SSH Console API Server as a standalone executable.

## Building the Executable

### Prerequisites

- Python 3.11 or higher
- All dependencies from `requirements.txt` installed
- PyInstaller installed (`pip install pyinstaller`)

### Build Process

#### Option 1: Using the build script (Linux/Mac)

```bash
./build.sh
```

#### Option 2: Manual build

```bash
# Install PyInstaller
pip install pyinstaller

# Clean previous builds
rm -rf build/ dist/

# Build the executable
pyinstaller build.spec
```

The executable will be created in the `dist/` directory:
- **Windows**: `dist/ssh-console-api.exe`
- **Linux**: `dist/ssh-console-api`

### Build Output

The build process creates a single-file executable that includes:
- Python runtime
- FastAPI and Uvicorn
- Paramiko SSH library
- All application code
- All dependencies

**Size**: Approximately 40-50 MB

## Deployment

### Basic Deployment

1. **Copy the executable** to your target system:
   ```bash
   # Windows
   copy dist\ssh-console-api.exe C:\path\to\destination\

   # Linux
   cp dist/ssh-console-api /path/to/destination/
   ```

2. **Create configuration file** in the same directory:
   ```bash
   # Copy the sample config
   cp config.ini /path/to/destination/
   ```

3. **Edit configuration**:
   - Change the default API key
   - Adjust settings as needed

4. **Run the executable**:
   ```bash
   # Windows
   ssh-console-api.exe

   # Linux
   ./ssh-console-api
   ```

### Directory Structure

```
deployment/
├── ssh-console-api(.exe)    # Executable
└── config.ini               # Configuration file
```

Runtime files will be created:
- `ssh_api.log` - Application log
- `audit.log` - Audit log (if enabled)

## Configuration for Production

### Security Checklist

Before deploying to production:

1. **Change the API key**:
   ```ini
   [server]
   api_key = generate-a-strong-random-key-here
   ```

2. **Enable IP whitelisting** (recommended):
   ```ini
   [security]
   enable_ip_whitelist = true
   allowed_ips = 10.0.0.0/8,192.168.1.0/24
   ```

3. **Configure rate limiting**:
   ```ini
   [security]
   rate_limit_enabled = true
   rate_limit_requests = 100
   rate_limit_window = 60
   ```

4. **Enable audit logging**:
   ```ini
   [security]
   enable_audit_log = true
   ```

5. **Bind to specific interface** (if needed):
   ```ini
   [server]
   host = 127.0.0.1  # Localhost only
   # or
   host = 0.0.0.0    # All interfaces
   ```

### Environment Variables

You can use environment variables instead of config.ini:

```bash
# Linux/Mac
export API_KEY="your-secret-key"
export SERVER_PORT=8000
export MAX_SESSIONS=100

# Windows
set API_KEY=your-secret-key
set SERVER_PORT=8000
set MAX_SESSIONS=100
```

## Running as a Service

### Linux (systemd)

1. **Create service file** `/etc/systemd/system/ssh-console-api.service`:

```ini
[Unit]
Description=SSH Console REST API Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ssh-console-api
ExecStart=/opt/ssh-console-api/ssh-console-api
Restart=always
RestartSec=10

# Environment
Environment="API_KEY=your-secret-key"
Environment="LOG_LEVEL=INFO"

[Install]
WantedBy=multi-user.target
```

2. **Enable and start service**:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ssh-console-api
sudo systemctl start ssh-console-api
sudo systemctl status ssh-console-api
```

3. **View logs**:

```bash
sudo journalctl -u ssh-console-api -f
```

### Windows Service

You can use `NSSM` (Non-Sucking Service Manager) to run as a Windows service:

1. **Download NSSM** from https://nssm.cc/download

2. **Install service**:

```cmd
nssm install SSHConsoleAPI "C:\path\to\ssh-console-api.exe"
nssm set SSHConsoleAPI AppDirectory "C:\path\to\"
nssm set SSHConsoleAPI DisplayName "SSH Console API Server"
nssm set SSHConsoleAPI Description "REST API for SSH remote command execution"
nssm set SSHConsoleAPI Start SERVICE_AUTO_START
```

3. **Start service**:

```cmd
nssm start SSHConsoleAPI
```

## Reverse Proxy Setup

### Nginx

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if added later)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Apache

```apache
<VirtualHost *:80>
    ServerName api.example.com

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    <Location />
        Require all granted
    </Location>
</VirtualHost>
```

## Docker Deployment (Alternative)

If you prefer containerization, create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY *.py ./
COPY config.ini ./

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "main.py"]
```

Build and run:

```bash
docker build -t ssh-console-api .
docker run -d -p 8000:8000 \
  -e API_KEY=your-secret-key \
  --name ssh-console-api \
  ssh-console-api
```

## Monitoring

### Health Check Endpoint

Monitor the service using the health endpoint:

```bash
curl http://localhost:8000/api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "active_sessions": 5,
  "uptime_seconds": 3600.5,
  "timestamp": "2025-11-12T10:00:00"
}
```

### Log Monitoring

Monitor logs for issues:

```bash
# Application log
tail -f ssh_api.log

# Audit log
tail -f audit.log
```

### Metrics

Consider integrating with monitoring tools:
- Prometheus (metrics endpoint can be added)
- Grafana (for visualization)
- ELK Stack (for log aggregation)

## Troubleshooting

### Executable won't start

1. Check if port is available:
   ```bash
   netstat -an | grep 8000
   ```

2. Check file permissions:
   ```bash
   chmod +x ssh-console-api
   ```

3. Check config.ini is present and valid

4. Run with debug logging:
   ```ini
   [logging]
   level = DEBUG
   ```

### High memory usage

Adjust session limits in config.ini:
```ini
[sessions]
max_sessions = 25
idle_timeout = 900
```

### Connection failures

1. Check SSH server is reachable
2. Verify credentials
3. Check firewall rules
4. Review audit.log for authentication failures

## Security Hardening

1. **Run as non-root user** (Linux)
2. **Use firewall rules** to restrict access
3. **Enable HTTPS** if exposing to internet
4. **Rotate API keys** regularly
5. **Monitor audit logs** for suspicious activity
6. **Keep dependencies updated**
7. **Use strong SSH credentials**
8. **Implement network segmentation**

## Backup and Recovery

### Configuration Backup

Backup these files:
- `config.ini`
- `ssh_api.log` (optional)
- `audit.log` (important for compliance)

### Session State

Sessions are in-memory only. If the service restarts, all sessions are lost. This is by design for security.

## Performance Tuning

### For high load:

1. **Increase worker processes** (if needed in future):
   ```ini
   [server]
   workers = 4
   ```

2. **Adjust session limits**:
   ```ini
   [sessions]
   max_sessions = 100
   ```

3. **Reduce cleanup interval**:
   ```ini
   [sessions]
   cleanup_interval = 30
   ```

4. **Use a reverse proxy** with caching

## Upgrading

To upgrade to a new version:

1. Stop the service
2. Backup config.ini
3. Replace the executable
4. Review config.ini for new options
5. Start the service
6. Check logs for any issues

## Support

For issues and questions:
- Check logs in `ssh_api.log` and `audit.log`
- Review this documentation
- Check the main README.md
- Create an issue in the project repository

## Appendix: Sample Production Configuration

```ini
[server]
host = 127.0.0.1
port = 8000
api_key = xP9$mK2#vL4&nQ7*wR1@zT6^yU3!hJ8
reload = false
workers = 1

[sessions]
max_sessions = 50
idle_timeout = 1800
max_command_timeout = 300
cleanup_interval = 60

[security]
enable_ip_whitelist = true
allowed_ips = 10.0.0.0/8,192.168.1.0/24
enable_audit_log = true
rate_limit_enabled = true
rate_limit_requests = 100
rate_limit_window = 60

[logging]
level = INFO
log_file = ssh_api.log
max_log_size = 10485760
backup_count = 10
```

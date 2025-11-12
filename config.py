"""
Configuration management for SSH Console API Server
"""
import os
import configparser
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv


class Config:
    """Application configuration manager"""

    def __init__(self, config_file: str = "config.ini"):
        """Initialize configuration"""
        self.config_file = config_file
        self.config = configparser.ConfigParser()

        # Load environment variables
        load_dotenv()

        # Load config file if exists
        if os.path.exists(config_file):
            self.config.read(config_file)
        else:
            self._create_default_config()

    def _create_default_config(self):
        """Create default configuration file"""
        self.config['server'] = {
            'host': '0.0.0.0',
            'port': '8000',
            'api_key': 'your-secret-api-key-here-change-this',
            'reload': 'false',
            'workers': '1'
        }

        self.config['sessions'] = {
            'max_sessions': '50',
            'idle_timeout': '1800',
            'max_command_timeout': '300',
            'cleanup_interval': '60'
        }

        self.config['security'] = {
            'enable_ip_whitelist': 'false',
            'allowed_ips': '127.0.0.1,192.168.1.0/24',
            'enable_audit_log': 'true',
            'rate_limit_enabled': 'true',
            'rate_limit_requests': '100',
            'rate_limit_window': '60',
            'cors_enabled': 'false',
            'cors_origins': ''
        }

        self.config['logging'] = {
            'level': 'INFO',
            'log_file': 'ssh_api.log',
            'max_log_size': '10485760',  # 10MB in bytes
            'backup_count': '5',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }

        # Write default config
        with open(self.config_file, 'w') as f:
            self.config.write(f)

    # Server Configuration
    @property
    def server_host(self) -> str:
        """Get server host"""
        return os.getenv('SERVER_HOST', self.config.get('server', 'host', fallback='0.0.0.0'))

    @property
    def server_port(self) -> int:
        """Get server port"""
        return int(os.getenv('SERVER_PORT', self.config.get('server', 'port', fallback='8000')))

    @property
    def api_key(self) -> str:
        """Get API key"""
        return os.getenv('API_KEY', self.config.get('server', 'api_key', fallback='your-secret-api-key-here-change-this'))

    @property
    def reload(self) -> bool:
        """Get reload setting for development"""
        return os.getenv('RELOAD', self.config.get('server', 'reload', fallback='false')).lower() == 'true'

    @property
    def workers(self) -> int:
        """Get number of workers"""
        return int(os.getenv('WORKERS', self.config.get('server', 'workers', fallback='1')))

    # Session Configuration
    @property
    def max_sessions(self) -> int:
        """Get maximum number of concurrent sessions"""
        return int(os.getenv('MAX_SESSIONS', self.config.get('sessions', 'max_sessions', fallback='50')))

    @property
    def idle_timeout(self) -> int:
        """Get idle timeout in seconds"""
        return int(os.getenv('IDLE_TIMEOUT', self.config.get('sessions', 'idle_timeout', fallback='1800')))

    @property
    def max_command_timeout(self) -> int:
        """Get maximum command timeout in seconds"""
        return int(os.getenv('MAX_COMMAND_TIMEOUT', self.config.get('sessions', 'max_command_timeout', fallback='300')))

    @property
    def cleanup_interval(self) -> int:
        """Get cleanup interval in seconds"""
        return int(os.getenv('CLEANUP_INTERVAL', self.config.get('sessions', 'cleanup_interval', fallback='60')))

    # Security Configuration
    @property
    def enable_ip_whitelist(self) -> bool:
        """Check if IP whitelist is enabled"""
        return os.getenv('ENABLE_IP_WHITELIST', self.config.get('security', 'enable_ip_whitelist', fallback='false')).lower() == 'true'

    @property
    def allowed_ips(self) -> List[str]:
        """Get list of allowed IPs"""
        ips_str = os.getenv('ALLOWED_IPS', self.config.get('security', 'allowed_ips', fallback='127.0.0.1'))
        return [ip.strip() for ip in ips_str.split(',')]

    @property
    def enable_audit_log(self) -> bool:
        """Check if audit logging is enabled"""
        return os.getenv('ENABLE_AUDIT_LOG', self.config.get('security', 'enable_audit_log', fallback='true')).lower() == 'true'

    @property
    def rate_limit_enabled(self) -> bool:
        """Check if rate limiting is enabled"""
        return os.getenv('RATE_LIMIT_ENABLED', self.config.get('security', 'rate_limit_enabled', fallback='true')).lower() == 'true'

    @property
    def rate_limit_requests(self) -> int:
        """Get rate limit requests per window"""
        return int(os.getenv('RATE_LIMIT_REQUESTS', self.config.get('security', 'rate_limit_requests', fallback='100')))

    @property
    def rate_limit_window(self) -> int:
        """Get rate limit window in seconds"""
        return int(os.getenv('RATE_LIMIT_WINDOW', self.config.get('security', 'rate_limit_window', fallback='60')))

    @property
    def cors_enabled(self) -> bool:
        """Check if CORS is enabled"""
        return os.getenv('CORS_ENABLED', self.config.get('security', 'cors_enabled', fallback='false')).lower() == 'true'

    @property
    def cors_origins(self) -> List[str]:
        """Get list of allowed CORS origins"""
        origins_str = os.getenv('CORS_ORIGINS', self.config.get('security', 'cors_origins', fallback=''))
        if not origins_str:
            return []
        return [origin.strip() for origin in origins_str.split(',')]

    # Logging Configuration
    @property
    def log_level(self) -> str:
        """Get logging level"""
        return os.getenv('LOG_LEVEL', self.config.get('logging', 'level', fallback='INFO'))

    @property
    def log_file(self) -> str:
        """Get log file path"""
        return os.getenv('LOG_FILE', self.config.get('logging', 'log_file', fallback='ssh_api.log'))

    @property
    def max_log_size(self) -> int:
        """Get maximum log file size in bytes"""
        return int(os.getenv('MAX_LOG_SIZE', self.config.get('logging', 'max_log_size', fallback='10485760')))

    @property
    def backup_count(self) -> int:
        """Get number of log backup files"""
        return int(os.getenv('BACKUP_COUNT', self.config.get('logging', 'backup_count', fallback='5')))

    @property
    def log_format(self) -> str:
        """Get log format string"""
        return os.getenv('LOG_FORMAT', self.config.get('logging', 'format',
                                                       fallback='%(asctime)s - %(name)s - %(levelname)s - %(message)s'))


# Global configuration instance
config = Config()

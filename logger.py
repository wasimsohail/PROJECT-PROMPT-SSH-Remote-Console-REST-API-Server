"""
Logging system for SSH Console API Server
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from datetime import datetime
from config import config


class AuditLogger:
    """Audit logger for tracking commands and security events"""

    def __init__(self, log_file: str = "audit.log"):
        """Initialize audit logger"""
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        # Create audit log handler
        handler = RotatingFileHandler(
            log_file,
            maxBytes=config.max_log_size,
            backupCount=config.backup_count
        )

        # Audit log format
        formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def log_command(self, session_id: str, host: str, username: str, command: str,
                    exit_code: Optional[int] = None, error: str = ""):
        """Log executed command"""
        message = (
            f"SESSION={session_id} | HOST={host} | USER={username} | "
            f"COMMAND={command} | EXIT_CODE={exit_code} | ERROR={error}"
        )
        self.logger.info(message)

    def log_session_create(self, session_id: str, host: str, username: str, label: Optional[str] = None):
        """Log session creation"""
        message = f"SESSION_CREATE | ID={session_id} | HOST={host} | USER={username} | LABEL={label}"
        self.logger.info(message)

    def log_session_close(self, session_id: str, host: str, reason: str = "normal"):
        """Log session closure"""
        message = f"SESSION_CLOSE | ID={session_id} | HOST={host} | REASON={reason}"
        self.logger.info(message)

    def log_auth_attempt(self, api_key: str, ip_address: str, success: bool):
        """Log authentication attempt"""
        # Mask API key for security
        masked_key = f"{api_key[:8]}..." if len(api_key) > 8 else "***"
        result = "SUCCESS" if success else "FAILED"
        message = f"AUTH_{result} | API_KEY={masked_key} | IP={ip_address}"
        self.logger.warning(message) if not success else self.logger.info(message)

    def log_security_event(self, event_type: str, details: str):
        """Log security event"""
        message = f"SECURITY_EVENT | TYPE={event_type} | DETAILS={details}"
        self.logger.warning(message)


def setup_logger(name: str = "ssh_api") -> logging.Logger:
    """
    Setup application logger with file and console handlers

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.log_level.upper()))
    logger.propagate = False

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatters
    formatter = logging.Formatter(config.log_format)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        config.log_file,
        maxBytes=config.max_log_size,
        backupCount=config.backup_count
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Global logger instances
app_logger = setup_logger("ssh_api")
audit_logger = AuditLogger() if config.enable_audit_log else None


def get_logger(name: str = "ssh_api") -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_audit_logger() -> Optional[AuditLogger]:
    """
    Get audit logger instance

    Returns:
        AuditLogger instance or None if audit logging is disabled
    """
    return audit_logger

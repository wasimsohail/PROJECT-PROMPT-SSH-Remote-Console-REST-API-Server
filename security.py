"""
Security and authentication for SSH Console API Server
"""
import ipaddress
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from config import config
from logger import get_logger, get_audit_logger

logger = get_logger(__name__)
audit_logger = get_audit_logger()

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class RateLimiter:
    """Rate limiter implementation"""

    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed based on rate limit

        Args:
            identifier: Client identifier (IP address or API key)

        Returns:
            True if request is allowed, False otherwise
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)

        # Clean old requests
        request_times = self.requests[identifier]
        while request_times and request_times[0] < cutoff:
            request_times.popleft()

        # Check if under limit
        if len(request_times) >= self.max_requests:
            return False

        # Add current request
        request_times.append(now)
        return True

    def get_remaining(self, identifier: str) -> int:
        """
        Get remaining requests for identifier

        Args:
            identifier: Client identifier

        Returns:
            Number of remaining requests
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)

        # Clean old requests
        request_times = self.requests[identifier]
        while request_times and request_times[0] < cutoff:
            request_times.popleft()

        return max(0, self.max_requests - len(request_times))


# Global rate limiter instance
rate_limiter = RateLimiter(
    max_requests=config.rate_limit_requests,
    window_seconds=config.rate_limit_window
) if config.rate_limit_enabled else None


def is_ip_allowed(ip_address: str) -> bool:
    """
    Check if IP address is in whitelist

    Args:
        ip_address: IP address to check

    Returns:
        True if allowed, False otherwise
    """
    if not config.enable_ip_whitelist:
        return True

    try:
        ip = ipaddress.ip_address(ip_address)

        for allowed in config.allowed_ips:
            # Check if it's a network (CIDR notation)
            if '/' in allowed:
                network = ipaddress.ip_network(allowed, strict=False)
                if ip in network:
                    return True
            # Check if it's a single IP
            else:
                if ip == ipaddress.ip_address(allowed):
                    return True

        return False

    except ValueError as e:
        logger.error(f"Invalid IP address format: {ip_address} - {e}")
        return False


async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Security(api_key_header)
) -> str:
    """
    Verify API key from request header

    Args:
        request: FastAPI request object
        api_key: API key from header

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is invalid or missing
    """
    client_ip = request.client.host if request.client else "unknown"

    # Check API key
    if not api_key:
        if audit_logger:
            audit_logger.log_auth_attempt("", client_ip, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "MISSING_API_KEY",
                    "message": "API key is required. Please provide X-API-Key header.",
                    "details": {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )

    if api_key != config.api_key:
        if audit_logger:
            audit_logger.log_auth_attempt(api_key, client_ip, False)
        logger.warning(f"Invalid API key attempt from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "Invalid API key provided.",
                    "details": {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )

    # Check IP whitelist
    if not is_ip_allowed(client_ip):
        if audit_logger:
            audit_logger.log_security_event("IP_NOT_WHITELISTED", f"IP={client_ip}")
        logger.warning(f"Request from non-whitelisted IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "IP_NOT_ALLOWED",
                    "message": "Your IP address is not authorized to access this API.",
                    "details": {"ip": client_ip},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )

    # Check rate limit
    if rate_limiter:
        identifier = f"{client_ip}:{api_key}"
        if not rate_limiter.is_allowed(identifier):
            if audit_logger:
                audit_logger.log_security_event("RATE_LIMIT_EXCEEDED", f"IP={client_ip}")
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Maximum {config.rate_limit_requests} requests per {config.rate_limit_window} seconds.",
                        "details": {
                            "retry_after": config.rate_limit_window
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )

    # Log successful authentication
    if audit_logger:
        audit_logger.log_auth_attempt(api_key, client_ip, True)

    return api_key


def get_rate_limit_info(request: Request) -> dict:
    """
    Get rate limit information for client

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with rate limit info
    """
    if not rate_limiter:
        return {}

    client_ip = request.client.host if request.client else "unknown"
    api_key = request.headers.get("X-API-Key", "")
    identifier = f"{client_ip}:{api_key}"

    remaining = rate_limiter.get_remaining(identifier)

    return {
        "X-RateLimit-Limit": str(config.rate_limit_requests),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Window": str(config.rate_limit_window)
    }

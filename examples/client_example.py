#!/usr/bin/env python3
"""
Example client for SSH Console API Server

This script demonstrates how to use the SSH Console API to:
- Create SSH sessions
- Execute commands
- Retrieve output
- Manage sessions

Usage:
    python client_example.py
"""

import requests
import json
import time
from typing import Optional, Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = "your-secret-api-key-here-change-this"

# SSH connection details (update these with your SSH server details)
SSH_HOST = "192.168.1.100"
SSH_PORT = 22
SSH_USERNAME = "admin"
SSH_PASSWORD = "password123"


class SSHAPIClient:
    """Client for SSH Console API"""

    def __init__(self, base_url: str, api_key: str):
        """
        Initialize API client

        Args:
            base_url: Base URL of the API server
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        kwargs['headers'] = self.headers

        try:
            response = requests.request(method, url, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        response = self._make_request("GET", "/api/v1/health")
        return response.json()

    def get_version(self) -> Dict[str, Any]:
        """Get API version"""
        response = self._make_request("GET", "/api/v1/version")
        return response.json()

    def test_connection(self, host: str, port: int, username: str, password: str) -> Dict[str, Any]:
        """
        Test SSH connection without creating session

        Args:
            host: SSH server host
            port: SSH server port
            username: SSH username
            password: SSH password

        Returns:
            Connection test result
        """
        data = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "auth_type": "password",
            "timeout": 10
        }

        response = self._make_request("POST", "/api/v1/test-connection", json=data)
        return response.json()

    def create_session(self, host: str, port: int, username: str, password: str,
                       label: Optional[str] = None) -> Dict[str, Any]:
        """
        Create new SSH session

        Args:
            host: SSH server host
            port: SSH server port
            username: SSH username
            password: SSH password
            label: Optional session label

        Returns:
            Session details
        """
        data = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "auth_type": "password",
            "timeout": 30
        }

        if label:
            data["label"] = label

        response = self._make_request("POST", "/api/v1/sessions", json=data)
        if response.status_code == 201:
            return response.json()
        else:
            error = response.json()
            raise Exception(f"Failed to create session: {error}")

    def list_sessions(self) -> Dict[str, Any]:
        """List all active sessions"""
        response = self._make_request("GET", "/api/v1/sessions")
        return response.json()

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session details"""
        response = self._make_request("GET", f"/api/v1/sessions/{session_id}")
        return response.json()

    def close_session(self, session_id: str) -> bool:
        """Close session"""
        response = self._make_request("DELETE", f"/api/v1/sessions/{session_id}")
        return response.status_code == 204

    def execute_command(self, session_id: str, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute command on session

        Args:
            session_id: Session ID
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            Command execution result
        """
        data = {
            "command": command,
            "timeout": timeout,
            "wait_for_output": True
        }

        response = self._make_request("POST", f"/api/v1/sessions/{session_id}/execute", json=data)
        return response.json()

    def get_output(self, session_id: str, clear: bool = False) -> Dict[str, Any]:
        """Get session output buffer"""
        params = {"clear": "true" if clear else "false"}
        response = self._make_request("GET", f"/api/v1/sessions/{session_id}/output", params=params)
        return response.json()

    def get_command_history(self, session_id: str) -> Dict[str, Any]:
        """Get command history for session"""
        response = self._make_request("GET", f"/api/v1/sessions/{session_id}/commands")
        return response.json()


def print_json(data: Dict[str, Any], title: Optional[str] = None):
    """Pretty print JSON data"""
    if title:
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print('=' * 60)
    print(json.dumps(data, indent=2))


def main():
    """Main example function"""
    print("SSH Console API Client Example")
    print("=" * 60)

    # Create API client
    client = SSHAPIClient(API_BASE_URL, API_KEY)

    try:
        # 1. Check API health
        print("\n1. Checking API health...")
        health = client.health_check()
        print_json(health, "Health Check")

        # 2. Get API version
        print("\n2. Getting API version...")
        version = client.get_version()
        print_json(version, "Version Info")

        # 3. Test SSH connection
        print(f"\n3. Testing SSH connection to {SSH_HOST}...")
        test_result = client.test_connection(SSH_HOST, SSH_PORT, SSH_USERNAME, SSH_PASSWORD)
        print_json(test_result, "Connection Test")

        if not test_result.get("success"):
            print("\nConnection test failed. Please check SSH server details.")
            print("Update SSH_HOST, SSH_USERNAME, and SSH_PASSWORD in this script.")
            return

        # 4. Create SSH session
        print(f"\n4. Creating SSH session to {SSH_HOST}...")
        session = client.create_session(
            SSH_HOST, SSH_PORT, SSH_USERNAME, SSH_PASSWORD,
            label="Example Session"
        )
        print_json(session, "New Session")
        session_id = session["session_id"]

        # 5. List all sessions
        print("\n5. Listing all sessions...")
        sessions = client.list_sessions()
        print_json(sessions, "Active Sessions")

        # 6. Execute commands
        commands_to_run = [
            "whoami",
            "pwd",
            "uname -a",
            "df -h",
            "ls -la"
        ]

        for cmd in commands_to_run:
            print(f"\n6. Executing command: {cmd}")
            result = client.execute_command(session_id, cmd)

            print(f"   Status: {result['status']}")
            print(f"   Exit Code: {result['exit_code']}")
            print(f"   Execution Time: {result['execution_time']:.2f}s")
            print(f"\n   Output:")
            print("   " + "\n   ".join(result['output'].split('\n')))

            if result['error']:
                print(f"\n   Error:")
                print("   " + "\n   ".join(result['error'].split('\n')))

            time.sleep(0.5)  # Small delay between commands

        # 7. Get command history
        print("\n7. Getting command history...")
        history = client.get_command_history(session_id)
        print_json(history, "Command History")

        # 8. Get output buffer
        print("\n8. Getting output buffer...")
        output = client.get_output(session_id)
        print(f"Buffered output length: {len(output['output'])} characters")

        # 9. Get session details
        print("\n9. Getting session details...")
        session_details = client.get_session(session_id)
        print_json(session_details, "Session Details")

        # 10. Close session
        print(f"\n10. Closing session {session_id}...")
        success = client.close_session(session_id)
        if success:
            print("Session closed successfully")
        else:
            print("Failed to close session")

        # 11. Verify session is closed
        print("\n11. Verifying session list...")
        sessions = client.list_sessions()
        print(f"Active sessions: {sessions['total_count']}")

        print("\n" + "=" * 60)
        print("Example completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("1. The API server is running (python main.py)")
        print("2. The API_KEY matches your config.ini")
        print("3. SSH server details are correct")


if __name__ == "__main__":
    main()

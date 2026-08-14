"""
KueryCore AI — Jules REST API Service Client
Provides async communication with Google's Jules REST API for autonomous coding sessions.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class JulesAPIError(Exception):
    """Raised when the Jules API returns an error or is unconfigured."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class JulesClient:
    """Async HTTP client for interacting with Jules REST API (v1alpha)."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.JULES_API_KEY
        self.base_url = (base_url or settings.JULES_BASE_URL).rstrip("/")

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise JulesAPIError(
                "Jules API key is not configured. Set JULES_API_KEY in environment variables.",
                status_code=400,
            )
        return {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def list_sources(self, page_size: Optional[int] = None, page_token: Optional[str] = None) -> Dict[str, Any]:
        """List available sources connected to Jules (e.g. GitHub repos)."""
        headers = self._get_headers()
        params = {}
        if page_size:
            params["pageSize"] = str(page_size)
        if page_token:
            params["pageToken"] = page_token

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/sources", headers=headers, params=params)
            if resp.status_code >= 400:
                raise JulesAPIError(f"Jules API list_sources failed: {resp.text}", status_code=resp.status_code)
            return resp.json()

    async def create_session(
        self,
        prompt: str,
        source: str,
        starting_branch: str = "main",
        automation_mode: str = "AUTO_CREATE_PR",
        title: Optional[str] = None,
        require_plan_approval: bool = False,
    ) -> Dict[str, Any]:
        """Create a new autonomous coding session."""
        headers = self._get_headers()
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "sourceContext": {
                "source": source,
                "githubRepoContext": {
                    "startingBranch": starting_branch,
                },
            },
            "automationMode": automation_mode,
        }
        if title:
            payload["title"] = title
        if require_plan_approval:
            payload["requirePlanApproval"] = True

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/sessions", headers=headers, json=payload)
            if resp.status_code >= 400:
                raise JulesAPIError(f"Jules API create_session failed: {resp.text}", status_code=resp.status_code)
            return resp.json()

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get details and status for a specific session."""
        headers = self._get_headers()
        session_name = session_id if session_id.startswith("sessions/") else f"sessions/{session_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/{session_name}", headers=headers)
            if resp.status_code >= 400:
                raise JulesAPIError(f"Jules API get_session failed: {resp.text}", status_code=resp.status_code)
            return resp.json()

    async def list_sessions(self, page_size: Optional[int] = None, page_token: Optional[str] = None) -> Dict[str, Any]:
        """List sessions created by the API key."""
        headers = self._get_headers()
        params = {}
        if page_size:
            params["pageSize"] = str(page_size)
        if page_token:
            params["pageToken"] = page_token

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/sessions", headers=headers, params=params)
            if resp.status_code >= 400:
                raise JulesAPIError(f"Jules API list_sessions failed: {resp.text}", status_code=resp.status_code)
            return resp.json()

    async def approve_plan(self, session_id: str) -> Dict[str, Any]:
        """Approve the latest plan for a session that requires plan approval."""
        headers = self._get_headers()
        session_name = session_id if session_id.startswith("sessions/") else f"sessions/{session_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/{session_name}:approvePlan", headers=headers, json={})
            if resp.status_code >= 400:
                raise JulesAPIError(f"Jules API approve_plan failed: {resp.text}", status_code=resp.status_code)
            return resp.json() if resp.content else {"status": "approved"}

    async def send_message(self, session_id: str, prompt: str) -> Dict[str, Any]:
        """Send a message/prompt to an active session."""
        headers = self._get_headers()
        session_name = session_id if session_id.startswith("sessions/") else f"sessions/{session_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/{session_name}:sendMessage",
                headers=headers,
                json={"prompt": prompt},
            )
            if resp.status_code >= 400:
                raise JulesAPIError(f"Jules API send_message failed: {resp.text}", status_code=resp.status_code)
            return resp.json() if resp.content else {"status": "sent"}

    async def list_activities(self, session_id: str, page_size: Optional[int] = None) -> Dict[str, Any]:
        """List activity log items for a session."""
        headers = self._get_headers()
        session_name = session_id if session_id.startswith("sessions/") else f"sessions/{session_id}"
        params = {}
        if page_size:
            params["pageSize"] = str(page_size)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/{session_name}/activities", headers=headers, params=params)
            if resp.status_code >= 400:
                raise JulesAPIError(f"Jules API list_activities failed: {resp.text}", status_code=resp.status_code)
            return resp.json()

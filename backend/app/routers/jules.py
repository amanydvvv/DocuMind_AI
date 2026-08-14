"""
KueryCore AI — Jules Admin Router
Admin endpoints for managing Jules REST API autonomous coding sessions.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user
from app.models.user import User
from app.schemas import (
    JulesCreateSessionRequest,
    JulesSendMessageRequest,
    JulesSessionResponse,
    JulesSourceListResponse,
)
from app.services.jules import JulesAPIError, JulesClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/jules", tags=["Jules AI Agent"])


@router.get("/sources", response_model=JulesSourceListResponse)
async def list_jules_sources(
    page_size: Optional[int] = Query(default=None, ge=1, le=100),
    page_token: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
):
    """List connected GitHub sources available to Jules."""
    client = JulesClient()
    try:
        data = await client.list_sources(page_size=page_size, page_token=page_token)
        return JulesSourceListResponse(
            sources=data.get("sources", []),
            next_page_token=data.get("nextPageToken"),
        )
    except JulesAPIError as exc:
        raise HTTPException(
            status_code=exc.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/sessions", response_model=JulesSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_jules_session(
    body: JulesCreateSessionRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new autonomous Jules coding session to edit code or generate a PR."""
    client = JulesClient()
    try:
        res = await client.create_session(
            prompt=body.prompt,
            source=body.source,
            starting_branch=body.starting_branch,
            automation_mode=body.automation_mode,
            title=body.title,
            require_plan_approval=body.require_plan_approval,
        )
        return JulesSessionResponse(
            name=res.get("name", ""),
            id=res.get("id", ""),
            title=res.get("title"),
            prompt=res.get("prompt"),
            state=res.get("state"),
            outputs=res.get("outputs"),
        )
    except JulesAPIError as exc:
        raise HTTPException(
            status_code=exc.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/sessions", response_model=list[JulesSessionResponse])
async def list_jules_sessions(
    page_size: Optional[int] = Query(default=None, ge=1, le=50),
    page_token: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
):
    """List active and past Jules sessions."""
    client = JulesClient()
    try:
        data = await client.list_sessions(page_size=page_size, page_token=page_token)
        raw_sessions = data.get("sessions", [])
        return [
            JulesSessionResponse(
                name=s.get("name", ""),
                id=s.get("id", ""),
                title=s.get("title"),
                prompt=s.get("prompt"),
                state=s.get("state"),
                outputs=s.get("outputs"),
            )
            for s in raw_sessions
        ]
    except JulesAPIError as exc:
        raise HTTPException(
            status_code=exc.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/sessions/{session_id}", response_model=JulesSessionResponse)
async def get_jules_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Fetch status and outputs (PR links, plans) for a specific Jules session."""
    client = JulesClient()
    try:
        res = await client.get_session(session_id)
        return JulesSessionResponse(
            name=res.get("name", ""),
            id=res.get("id", ""),
            title=res.get("title"),
            prompt=res.get("prompt"),
            state=res.get("state"),
            outputs=res.get("outputs"),
        )
    except JulesAPIError as exc:
        raise HTTPException(
            status_code=exc.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/sessions/{session_id}/message")
async def send_jules_message(
    session_id: str,
    body: JulesSendMessageRequest,
    current_user: User = Depends(get_current_user),
):
    """Send a follow-up prompt to an active Jules session."""
    client = JulesClient()
    try:
        res = await client.send_message(session_id, body.prompt)
        return res
    except JulesAPIError as exc:
        raise HTTPException(
            status_code=exc.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/sessions/{session_id}/approve")
async def approve_jules_plan(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Approve the proposed execution plan for a session."""
    client = JulesClient()
    try:
        res = await client.approve_plan(session_id)
        return res
    except JulesAPIError as exc:
        raise HTTPException(
            status_code=exc.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

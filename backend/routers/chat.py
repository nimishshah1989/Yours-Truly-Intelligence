"""AI Chat router — session CRUD and Claude agent message handling."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from database import get_db, get_readonly_db
from dependencies import get_restaurant_id
from models import ChatMessage, ChatSession, ConversationMemory, Restaurant

logger = logging.getLogger("ytip.chat")
router = APIRouter(prefix="/api/chat", tags=["AI Chat"])


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------
class CreateSessionRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=200)


class SessionResponse(BaseModel):
    id: int
    title: Optional[str]
    message_count: int = 0
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    widgets: Optional[List[Dict[str, Any]]] = None
    created_at: str


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ts(dt: Optional[datetime]) -> str:
    """Safely convert a datetime to ISO string."""
    return dt.isoformat() if dt else datetime.utcnow().isoformat()


def _to_session_response(session: ChatSession, message_count: int = 0) -> SessionResponse:
    """Convert a ChatSession ORM object to its API response model."""
    return SessionResponse(
        id=session.id,
        title=session.title,
        message_count=message_count,
        created_at=_ts(session.created_at),
        updated_at=_ts(session.updated_at),
    )


def _to_message_response(msg: ChatMessage) -> MessageResponse:
    """Convert a ChatMessage ORM object to its API response model."""
    return MessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role,
        content=msg.content,
        widgets=msg.widgets if msg.widgets else None,
        created_at=_ts(msg.created_at),
    )


def _categorize_query(query: str) -> str:
    """Simple keyword-based query categorization."""
    q = query.lower()
    if any(w in q for w in ["food cost", "cogs", "ingredient", "portion", "recipe", "consumption"]):
        return "food_cost"
    if any(w in q for w in ["menu", "item", "dish", "star", "dog", "margin"]):
        return "menu"
    if any(w in q for w in ["zomato", "swiggy", "channel", "delivery", "commission", "aggregator"]):
        return "channel"
    if any(w in q for w in ["vendor", "purchase", "supplier", "price"]):
        return "vendor"
    if any(w in q for w in ["staff", "labor", "employee", "shift"]):
        return "staffing"
    if any(w in q for w in ["revenue", "sales", "order", "ticket"]):
        return "revenue"
    return "general"


def _get_session_or_404(db: Session, session_id: int, restaurant_id: int) -> ChatSession:
    """Fetch a session scoped to the restaurant, or raise 404."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.restaurant_id == restaurant_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/sessions", response_model=SessionResponse, status_code=201)
def create_session(
    body: CreateSessionRequest,
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_db),
):
    """Create a new chat session."""
    try:
        session = ChatSession(
            restaurant_id=restaurant_id,
            title=body.title or "New conversation",
        )
        db.add(session)
        db.flush()
        return _to_session_response(session, message_count=0)
    except Exception as exc:
        logger.error("[API] POST /api/chat/sessions failed: %s | rid=%d", exc, restaurant_id)
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
):
    """List all chat sessions for the restaurant, newest first (max 50)."""
    try:
        sessions = db.query(ChatSession).filter(
            ChatSession.restaurant_id == restaurant_id,
        ).order_by(ChatSession.updated_at.desc()).limit(50).all()

        # Bulk-fetch message counts to avoid N+1 queries
        session_ids = [s.id for s in sessions]
        counts = (
            db.query(ChatMessage.session_id, sa_func.count(ChatMessage.id))
            .filter(ChatMessage.session_id.in_(session_ids))
            .group_by(ChatMessage.session_id)
            .all()
        )
        count_map: Dict[int, int] = {sid: cnt for sid, cnt in counts}

        return [
            _to_session_response(s, message_count=count_map.get(s.id, 0))
            for s in sessions
        ]
    except Exception as exc:
        logger.error("[API] GET /api/chat/sessions failed: %s | rid=%d", exc, restaurant_id)
        raise HTTPException(status_code=500, detail="Failed to list sessions")


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
def get_messages(
    session_id: int,
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
):
    """Retrieve all messages in a chat session, ordered chronologically."""
    try:
        _get_session_or_404(db, session_id, restaurant_id)

        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.restaurant_id == restaurant_id,
        ).order_by(ChatMessage.created_at).all()

        return [_to_message_response(m) for m in messages]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[API] GET /api/chat/sessions/%d/messages failed: %s | rid=%d",
            session_id, exc, restaurant_id,
        )
        raise HTTPException(status_code=500, detail="Failed to load messages")


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse, status_code=201)
def send_message(
    session_id: int,
    body: SendMessageRequest,
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_db),
):
    """Send a user message and get Claude's response with optional widgets."""
    # Verify session ownership
    session = _get_session_or_404(db, session_id, restaurant_id)

    # Resolve restaurant name for the agent system prompt
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    restaurant_name = restaurant.name if restaurant else "Restaurant"

    # Persist user message
    user_msg = ChatMessage(
        restaurant_id=restaurant_id,
        session_id=session_id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    db.flush()

    # Build conversation history from prior messages (excludes the just-inserted user msg)
    prior_messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.restaurant_id == restaurant_id,
        ChatMessage.id != user_msg.id,
    ).order_by(ChatMessage.created_at).all()

    conversation_history = [{"role": m.role, "content": m.content} for m in prior_messages]

    # Run the Claude agent (uses its own read-only session for SQL execution)
    try:
        from agent.agent import run_agent

        text_response, widgets = run_agent(
            message=body.content,
            restaurant_id=restaurant_id,
            restaurant_name=restaurant_name,
            conversation_history=conversation_history if conversation_history else None,
        )
    except Exception as exc:
        logger.error(
            "Agent call failed for session %d: %s | rid=%d, input=%s",
            session_id, exc, restaurant_id, body.content[:200],
        )
        text_response = (
            "I'm sorry, I encountered an error processing your request. "
            "Please try again in a moment."
        )
        widgets = []

    # Persist assistant message
    assistant_msg = ChatMessage(
        restaurant_id=restaurant_id,
        session_id=session_id,
        role="assistant",
        content=text_response,
        widgets=widgets if widgets else None,
    )
    db.add(assistant_msg)
    db.flush()

    # Log to conversation memory
    try:
        memory = ConversationMemory(
            restaurant_id=restaurant_id,
            channel="web",
            query_text=body.content,
            response_summary=text_response[:500],
            query_category=_categorize_query(body.content),
            owner_engaged=False,
        )
        db.add(memory)
        db.flush()
    except Exception:
        pass  # never break chat for memory logging failure

    # Auto-title: set session title to first user message (truncated)
    if not prior_messages and body.content:
        session.title = body.content[:100]

    return SendMessageResponse(
        user_message=_to_message_response(user_msg),
        assistant_message=_to_message_response(assistant_msg),
    )


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_db),
):
    """Delete a chat session and all its messages."""
    try:
        session = _get_session_or_404(db, session_id, restaurant_id)

        # Delete messages first (FK constraint)
        db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.restaurant_id == restaurant_id,
        ).delete(synchronize_session="fetch")

        db.delete(session)
        db.flush()
        return None
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[API] DELETE /api/chat/sessions/%d failed: %s | rid=%d",
            session_id, exc, restaurant_id,
        )
        raise HTTPException(status_code=500, detail="Failed to delete session")

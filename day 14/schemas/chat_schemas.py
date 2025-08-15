# /schemas/chat_schemas.py

from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    """Represents a single message in the chat history."""
    role: str
    text: str

class ChatHistoryResponse(BaseModel):
    """Response model for fetching chat history."""
    history: List[Message]

class AgentChatResponse(BaseModel):
    """Response model for a successful chat interaction."""
    history: List[Message]
    audio_url: Optional[str] = None

class ErrorResponse(BaseModel):
    """Response model for errors, includes context."""
    error: str
    history: List[Message]
    audio_url: Optional[str] = None
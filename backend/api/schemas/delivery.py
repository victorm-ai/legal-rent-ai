"""API schemas for reports, chat and notifications."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GenerateReportRequest(BaseModel):
    format: str = Field(..., pattern="^(pdf|json)$")


class ReportResponse(BaseModel):
    id: str
    analysis_id: str
    format: str
    generated_by: str
    generated_at: datetime


class CreateChatSessionRequest(BaseModel):
    analysis_id: str


class ChatSessionResponse(BaseModel):
    id: str
    contract_id: str
    analysis_id: str
    created_at: datetime


class SendChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class ChatReferenceResponse(BaseModel):
    type: str
    id: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    title: Optional[str] = None
    code: Optional[str] = None
    article: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    references: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class ChatSuggestionsResponse(BaseModel):
    suggestions: List[str]


class NotifyLawyerRequest(BaseModel):
    lawyer_email: str = Field(..., min_length=5, max_length=320)
    decision: str = Field(..., min_length=10, max_length=5000)


class NotificationResponse(BaseModel):
    id: str
    analysis_id: str
    lawyer_email: str
    decision: str
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime


class SendReviewMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class ReviewMessageResponse(BaseModel):
    id: str
    analysis_id: str
    user_id: str
    author_name: str
    author_email: str
    author_role: str
    content: str
    created_at: datetime

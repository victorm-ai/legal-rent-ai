"""DTOs for reports, chat and notifications (RF-41–RF-51)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ReportDTO:
    id: str
    analysis_id: str
    format: str
    storage_path: str
    generated_by: str
    generated_at: datetime


@dataclass
class ChatSessionDTO:
    id: str
    contract_id: str
    user_id: str
    analysis_id: str
    created_at: datetime


@dataclass
class ChatMessageDTO:
    id: str
    session_id: str
    role: str
    content: str
    references: List[Dict[str, Any]] = field(default_factory=list)
    created_at: Optional[datetime] = None


@dataclass
class NotificationDTO:
    id: str
    analysis_id: str
    user_id: str
    lawyer_email: str
    decision: str
    status: str
    sent_at: Optional[datetime]
    created_at: datetime


@dataclass
class ReviewMessageDTO:
    id: str
    analysis_id: str
    user_id: str
    author_name: str
    author_email: str
    author_role: str
    content: str
    created_at: datetime

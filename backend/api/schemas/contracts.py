"""Contract API schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ContractDocumentResponse(BaseModel):
    id: str
    file_name: str
    document_type: str
    mime_type: Optional[str] = None
    file_size_bytes: int
    page_count: Optional[int] = None
    extraction_method: Optional[str] = None
    is_signed_version: bool = False
    uploaded_at: datetime


class ContractPartyResponse(BaseModel):
    party_type: str
    name: str
    legal_representative: Optional[str] = None
    confidence: Optional[float] = None
    source_page: Optional[int] = None


class ContractUpdateRequest(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = None
    closure_notes: Optional[str] = Field(default=None, max_length=5000)


class DocumentTextResponse(BaseModel):
    document_id: str
    text: str
    extraction_method: Optional[str] = None
    page_count: Optional[int] = None
    character_count: int


class DownloadTokenResponse(BaseModel):
    token: str
    expires_at: datetime
    download_path: str


class ContractResponse(BaseModel):
    id: str
    user_id: str
    perspective: str
    jurisdiction: Optional[str] = None
    status: str
    title: Optional[str] = None
    closure_notes: Optional[str] = None
    documents: List[ContractDocumentResponse] = Field(default_factory=list)
    parties: List[ContractPartyResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ContractSummaryResponse(BaseModel):
    id: str
    user_id: str
    perspective: str
    jurisdiction: Optional[str] = None
    status: str
    title: Optional[str] = None
    document_count: int
    document_types: List[str] = Field(default_factory=list)
    parties: List[ContractPartyResponse] = Field(default_factory=list)
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    purge_eligible_at: Optional[datetime] = None
    unread_review_messages: int = 0
    created_at: datetime
    updated_at: datetime

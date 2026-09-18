"""Contract and document DTOs."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class ContractPartyDTO:
    party_type: str
    name: str
    legal_representative: Optional[str]
    confidence: Optional[float]
    source_page: Optional[int] = None


@dataclass
class ContractDocumentDTO:
    id: str
    contract_id: str
    file_name: str
    file_size_bytes: int
    document_type: str
    mime_type: Optional[str]
    page_count: Optional[int]
    extraction_method: Optional[str]
    uploaded_at: datetime
    is_signed_version: bool = False


@dataclass
class ContractDTO:
    id: str
    user_id: str
    perspective: str
    jurisdiction: Optional[str]
    status: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    documents: List[ContractDocumentDTO]
    closure_notes: Optional[str] = None
    parties: List[ContractPartyDTO] = None

    def __post_init__(self) -> None:
        if self.parties is None:
            self.parties = []


@dataclass
class ContractSummaryDTO:
    id: str
    user_id: str
    perspective: str
    jurisdiction: Optional[str]
    status: str
    title: Optional[str]
    document_count: int
    document_types: List[str]
    is_deleted: bool
    deleted_at: Optional[datetime]
    purge_eligible_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    unread_review_messages: int = 0
    parties: List[ContractPartyDTO] = None

    def __post_init__(self) -> None:
        if self.parties is None:
            self.parties = []

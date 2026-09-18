"""Retention policy API schemas (RF-54)."""

from pydantic import BaseModel


class RetentionPolicyResponse(BaseModel):
    soft_delete_retention_days: int
    description: str


class RetentionStatusResponse(BaseModel):
    soft_delete_retention_days: int
    purge_eligible_count: int
    skipped_with_dependencies_count: int


class RetentionPurgeResponse(BaseModel):
    purged_contracts: int
    skipped_contracts: int
    soft_delete_retention_days: int

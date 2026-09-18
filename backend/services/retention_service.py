"""Document retention policy (RF-54)."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from config.settings import Settings, get_settings
from data.repositories.contract_repository import ContractRepository


@dataclass(frozen=True)
class RetentionPolicy:
    """Public retention policy definition."""

    soft_delete_retention_days: int
    description: str


@dataclass(frozen=True)
class RetentionStatus:
    """Retention purge status for operational maintenance."""

    soft_delete_retention_days: int
    purge_eligible_count: int
    skipped_with_dependencies_count: int


@dataclass(frozen=True)
class RetentionPurgeResult:
    """Result of a retention purge operation."""

    purged_contracts: int
    skipped_contracts: int
    soft_delete_retention_days: int


class RetentionService:
    """Applies the basic document retention policy."""

    def __init__(
        self,
        contract_repository: ContractRepository | None = None,
        settings: Settings | None = None,
    ):
        self._settings = settings or get_settings()
        self._contracts = contract_repository or ContractRepository(self._settings)

    def get_policy(self) -> RetentionPolicy:
        """Return the configured retention policy."""
        days = self._settings.soft_delete_retention_days
        return RetentionPolicy(
            soft_delete_retention_days=days,
            description=(
                "Active contracts and documents are kept while in use. "
                f"Soft-deleted records are retained for {days} days before "
                "they become eligible for permanent removal per retention policy."
            ),
        )

    def get_status(self) -> RetentionStatus:
        """Return how many soft-deleted contracts are eligible for purge."""
        days = self._settings.soft_delete_retention_days
        cutoff = self._cutoff_datetime(days)
        eligible_ids = self._contracts.list_purge_eligible_ids(cutoff)
        skipped = self._contracts.count_soft_deleted_with_dependencies(cutoff)
        return RetentionStatus(
            soft_delete_retention_days=days,
            purge_eligible_count=len(eligible_ids),
            skipped_with_dependencies_count=skipped,
        )

    def purge_expired(self) -> RetentionPurgeResult:
        """Permanently remove soft-deleted contracts past the retention window."""
        days = self._settings.soft_delete_retention_days
        cutoff = self._cutoff_datetime(days)
        eligible_ids = self._contracts.list_purge_eligible_ids(cutoff)
        skipped = self._contracts.count_soft_deleted_with_dependencies(cutoff)

        purged = 0
        for contract_id in eligible_ids:
            if self._contracts.hard_delete_soft_deleted(contract_id):
                purged += 1

        return RetentionPurgeResult(
            purged_contracts=purged,
            skipped_contracts=skipped,
            soft_delete_retention_days=days,
        )

    @staticmethod
    def purge_eligible_at(deleted_at: datetime, retention_days: int) -> datetime:
        """Calculate when a soft-deleted record becomes eligible for purge."""
        if deleted_at.tzinfo is None:
            deleted_at = deleted_at.replace(tzinfo=timezone.utc)
        return deleted_at + timedelta(days=retention_days)

    @staticmethod
    def _cutoff_datetime(retention_days: int) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=retention_days)

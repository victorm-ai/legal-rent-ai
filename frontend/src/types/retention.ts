export interface RetentionPolicy {
  soft_delete_retention_days: number;
  description: string;
}

export interface RetentionStatus {
  soft_delete_retention_days: number;
  purge_eligible_count: number;
  skipped_with_dependencies_count: number;
}

export interface RetentionPurgeResult {
  purged_contracts: number;
  skipped_contracts: number;
  soft_delete_retention_days: number;
}

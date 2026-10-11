import { DOCUMENT_TYPE_LABELS } from '../config';
import type { ContractStatus } from '../types/contracts';

export const FINAL_APPROVED_LAWYER_REVISION_LABEL = 'Final approved version';

export function documentTypeDisplayLabel(
  documentType: string,
  contractStatus?: string | null,
): string {
  if (documentType === 'lawyer_revision' && contractStatus === 'terminated') {
    return FINAL_APPROVED_LAWYER_REVISION_LABEL;
  }
  return DOCUMENT_TYPE_LABELS[documentType] ?? documentType;
}

export function isContractLocked(status: string): boolean {  return status === 'terminated';
}

export function clientCanApproveEditedContract(
  role: string | undefined,
  status: string,
): boolean {
  return role === 'client' && status === 'in_review';
}

export function lawyerMustCloseWithNotes(
  role: string | undefined,
  fromStatus: string,
  toStatus: string,
): boolean {
  return role === 'lawyer' && fromStatus === 'approved' && toStatus === 'terminated';
}

export type { ContractStatus };

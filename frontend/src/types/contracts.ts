export type ContractPerspective = 'landlord' | 'tenant' | 'neutral';

export type ContractDocumentType = 'main_contract' | 'annex' | 'other' | 'lawyer_revision';

export type ContractStatus =
  | 'draft'
  | 'in_review'
  | 'approved'
  | 'in_signing'
  | 'signed'
  | 'expired'
  | 'terminated';

export interface ContractDocument {
  id: string;
  file_name: string;
  document_type: ContractDocumentType;
  mime_type: string | null;
  file_size_bytes: number;
  page_count: number | null;
  extraction_method: string | null;
  uploaded_at: string;
}

export interface ContractParty {
  party_type: string;
  name: string;
  legal_representative: string | null;
  confidence: number | null;
  source_page?: number | null;
}

export interface Contract {
  id: string;
  user_id: string;
  perspective: ContractPerspective;
  jurisdiction: string | null;
  status: string;
  title: string | null;
  closure_notes?: string | null;
  documents: ContractDocument[];
  parties: ContractParty[];
  created_at: string;
  updated_at: string;
}

export interface ContractSummary {
  id: string;
  user_id: string;
  perspective: ContractPerspective;
  jurisdiction: string | null;
  status: string;
  title: string | null;
  document_count: number;
  document_types: ContractDocumentType[];
  parties: ContractParty[];
  is_deleted: boolean;
  deleted_at: string | null;
  purge_eligible_at: string | null;
  unread_review_messages: number;
  created_at: string;
  updated_at: string;
}

export interface CreateContractParams {
  file: File;
  perspective: ContractPerspective;
  title?: string;
}

export interface UpdateContractParams {
  status?: ContractStatus;
  title?: string;
  closure_notes?: string;
}

export interface DocumentText {
  document_id: string;
  text: string;
  extraction_method: string | null;
  page_count: number | null;
  character_count: number;
}

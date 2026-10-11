export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
export const TOKEN_KEY = 'contract_analyzer_token';
export const USER_KEY = 'contract_analyzer_user';

export const ROLE_LABELS: Record<string, string> = {
  lawyer: 'Lawyer',
  client: 'Client',
};

export const STATUS_LABELS: Record<string, string> = {
  draft: 'Uploaded',
  in_review: 'In review',
  approved: 'Approved',
  in_signing: 'Signing in progress',
  signed: 'Signed',
  expired: 'Expired',
  terminated: 'Terminated',
  pending: 'Pending',
  rejected: 'Rejected',
};

export const PERSPECTIVE_LABELS: Record<string, string> = {
  landlord: 'Landlord',
  tenant: 'Tenant',
  neutral: 'Neutral',
};

export const PARTY_TYPE_LABELS: Record<string, string> = {
  landlord: 'Landlord',
  tenant: 'Tenant',
  guarantor: 'Guarantor',
  joint_obligor: 'Joint obligor',
  landlord_representative: 'Landlord representative',
  tenant_representative: 'Tenant representative',
};

export const DEFAULT_ANALYSIS_PERSPECTIVE = 'tenant' as const;

export const DEFAULT_ANALYSIS_DOCUMENT_SCOPE = 'original' as const;
export const EDITED_ANALYSIS_DOCUMENT_SCOPE = 'lawyer_revision' as const;

export const ANALYSIS_DOCUMENT_SCOPE_LABELS: Record<string, string> = {
  original: 'Original contract',
  lawyer_revision: 'Edited contract',
};

export const CONTRACT_PERSPECTIVES = [DEFAULT_ANALYSIS_PERSPECTIVE] as const;

export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  main_contract: 'Original contract',
  annex: 'Annex',
  other: 'Other document',
  lawyer_revision: 'Edited version',
};

export const ANALYSIS_STATUS_LABELS: Record<string, string> = {
  processing: 'Processing',
  ai_generated: 'AI generated',
  pending_review: 'Pending review',
  reviewed: 'Reviewed',
  approved: 'Approved',
  failed: 'Failed',
};

export const RISK_LABELS: Record<string, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
};

export const CLAUSE_CATEGORY_LABELS: Record<string, string> = {
  object: 'Subject matter',
  rent: 'Rent',
  deposit: 'Deposit',
  term: 'Term',
  maintenance: 'Maintenance',
  services: 'Utilities / services',
  sublease: 'Sublease',
  guarantees: 'Guarantees',
  insurance: 'Insurance',
  renewal: 'Renewal',
  termination: 'Termination',
  penalties: 'Penalties',
  liability: 'Liability',
  jurisdiction: 'Jurisdiction',
  other: 'Other',
};

export const FINDING_TYPE_LABELS: Record<string, string> = {
  legal_rule: 'Legal rule',
  best_practice: 'Best practice',
  missing_clause: 'Missing clause',
  contradiction: 'Contradiction',
  inconsistency: 'Inconsistency',
  unfavorable_clause: 'Unfavorable clause',
  obligation: 'Obligation',
};

export const FINDING_VERDICT_LABELS: Record<string, string> = {
  correct: 'Correct',
  incorrect: 'Incorrect',
  not_relevant: 'Not relevant',
};

export const EXTRACTED_FIELD_LABELS: Record<string, string> = {
  arrendador: 'Landlord',
  arrendatario: 'Tenant',
  fiador: 'Guarantor',
  obligado_solidario: 'Joint obligor',
  inmueble_direccion: 'Property address',
  inmueble_uso: 'Property use',
  inmueble_superficie: 'Property area',
  renta_mensual: 'Monthly rent',
  deposito: 'Deposit',
  garantia: 'Guarantee',
  fecha_inicio: 'Start date',
  fecha_fin: 'End date',
  duracion_meses: 'Duration (months)',
  jurisdiccion: 'Jurisdiction',
  representante_arrendador: 'Landlord representative',
  representante_arrendatario: 'Tenant representative',
  forma_pago: 'Payment method',
  impuestos: 'Taxes',
  incremento_renta: 'Rent increase',
  penalizacion: 'Penalty',
  mantenimiento: 'Maintenance',
  servicios: 'Utilities / services',
  renovacion: 'Renewal',
  terminacion: 'Termination',
};

export const MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024;

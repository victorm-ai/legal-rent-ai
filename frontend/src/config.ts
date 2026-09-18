export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
export const TOKEN_KEY = 'contract_analyzer_token';
export const USER_KEY = 'contract_analyzer_user';

export const ROLE_LABELS: Record<string, string> = {
  lawyer: 'Abogado',
  client: 'Cliente',
};

export const STATUS_LABELS: Record<string, string> = {
  draft: 'Cargado',
  in_review: 'En revisión',
  approved: 'Aprobado',
  in_signing: 'En firma',
  signed: 'Firmado',
  expired: 'Vencido',
  terminated: 'Terminado',
  pending: 'Pendiente',
  rejected: 'Rechazado',
};

export const PERSPECTIVE_LABELS: Record<string, string> = {
  landlord: 'Arrendador',
  tenant: 'Arrendatario',
  neutral: 'Neutral',
};

export const PARTY_TYPE_LABELS: Record<string, string> = {
  landlord: 'Arrendador',
  tenant: 'Arrendatario',
  guarantor: 'Fiador',
  joint_obligor: 'Obligado solidario',
  landlord_representative: 'Representante del arrendador',
  tenant_representative: 'Representante del arrendatario',
};

export const DEFAULT_ANALYSIS_PERSPECTIVE = 'tenant' as const;

export const DEFAULT_ANALYSIS_DOCUMENT_SCOPE = 'original' as const;
export const EDITED_ANALYSIS_DOCUMENT_SCOPE = 'lawyer_revision' as const;

export const ANALYSIS_DOCUMENT_SCOPE_LABELS: Record<string, string> = {
  original: 'Contrato original',
  lawyer_revision: 'Contrato editado',
};

export const CONTRACT_PERSPECTIVES = [DEFAULT_ANALYSIS_PERSPECTIVE] as const;

export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  main_contract: 'Contrato original',
  annex: 'Anexo',
  other: 'Otro documento',
  lawyer_revision: 'Versión editada',
};

export const ANALYSIS_STATUS_LABELS: Record<string, string> = {
  processing: 'Procesando',
  ai_generated: 'Generado por IA',
  pending_review: 'Pendiente de revisión',
  reviewed: 'Revisado',
  approved: 'Aprobado',
  failed: 'Fallido',
};

export const RISK_LABELS: Record<string, string> = {
  low: 'Bajo',
  medium: 'Medio',
  high: 'Alto',
};

export const CLAUSE_CATEGORY_LABELS: Record<string, string> = {
  object: 'Objeto',
  rent: 'Renta',
  deposit: 'Depósito',
  term: 'Vigencia',
  maintenance: 'Mantenimiento',
  services: 'Servicios',
  sublease: 'Subarrendamiento',
  guarantees: 'Garantías',
  insurance: 'Seguros',
  renewal: 'Renovación',
  termination: 'Terminación',
  penalties: 'Penalizaciones',
  liability: 'Responsabilidad',
  jurisdiction: 'Jurisdicción',
  other: 'Otro',
};

export const FINDING_TYPE_LABELS: Record<string, string> = {
  legal_rule: 'Regla legal',
  best_practice: 'Buena práctica',
  missing_clause: 'Cláusula faltante',
  contradiction: 'Contradicción',
  inconsistency: 'Inconsistencia',
  unfavorable_clause: 'Cláusula desfavorable',
  obligation: 'Obligación',
};

export const FINDING_VERDICT_LABELS: Record<string, string> = {
  correct: 'Correcto',
  incorrect: 'Incorrecto',
  not_relevant: 'No relevante',
};

export const EXTRACTED_FIELD_LABELS: Record<string, string> = {
  arrendador: 'Arrendador',
  arrendatario: 'Arrendatario',
  fiador: 'Fiador',
  obligado_solidario: 'Obligado solidario',
  inmueble_direccion: 'Dirección del inmueble',
  inmueble_uso: 'Uso del inmueble',
  inmueble_superficie: 'Superficie del inmueble',
  renta_mensual: 'Renta mensual',
  deposito: 'Depósito',
  garantia: 'Garantía',
  fecha_inicio: 'Fecha de inicio',
  fecha_fin: 'Fecha de fin',
  duracion_meses: 'Duración (meses)',
  jurisdiccion: 'Jurisdicción',
  representante_arrendador: 'Representante del arrendador',
  representante_arrendatario: 'Representante del arrendatario',
  forma_pago: 'Forma de pago',
  impuestos: 'Impuestos',
  incremento_renta: 'Incremento de renta',
  penalizacion: 'Penalización',
  mantenimiento: 'Mantenimiento',
  servicios: 'Servicios',
  renovacion: 'Renovación',
  terminacion: 'Terminación',
};

export const MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024;

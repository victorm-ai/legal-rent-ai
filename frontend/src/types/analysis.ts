export type AnalysisStatus =
  | 'processing'
  | 'ai_generated'
  | 'pending_review'
  | 'reviewed'
  | 'approved'
  | 'failed';

export type RiskLevel = 'low' | 'medium' | 'high';

export type ContractPerspective = 'landlord' | 'tenant' | 'neutral';

export type AnalysisDocumentScope = 'original' | 'lawyer_revision';

export interface SourceReference {
  page: number | null;
  clause: string | null;
  section: string | null;
  text_snippet: string | null;
}

export interface ExtractedFieldValue {
  value: string;
  confidence: number;
  requires_review: boolean;
  source: SourceReference | null;
}

export type FindingType =
  | 'legal_rule'
  | 'best_practice'
  | 'missing_clause'
  | 'contradiction'
  | 'inconsistency'
  | 'unfavorable_clause'
  | 'obligation';

export interface LegalCitation {
  id: string;
  law_code: string;
  article: string | null;
  excerpt: string | null;
  source_uri: string | null;
}

export type FindingVerdict = 'correct' | 'incorrect' | 'not_relevant';

export interface FindingReview {
  id: string;
  verdict: FindingVerdict;
  notes: string | null;
  lawyer_id: string;
  created_at: string;
}

export interface AnalysisApproval {
  id: string;
  analysis_id: string;
  lawyer_id: string;
  approved_at: string;
  notes: string | null;
}

export interface AnalysisFinding {
  id: string;
  finding_type: FindingType;
  severity: RiskLevel;
  title: string;
  description: string;
  sort_order: number;
  clause_id: string | null;
  legal_basis: string | null;
  source_law: string | null;
  evidence_text: string | null;
  evidence_page: number | null;
  recommendation: string | null;
  suggested_rewording: string | null;
  confidence?: number | null;
  legal_citations: LegalCitation[];
  review: FindingReview | null;
}

export interface AnalysisClause {
  id: string;
  category: string;
  text: string;
  section: string | null;
  page: number | null;
  confidence: number;
}

export interface AnalysisSummary {
  id: string;
  contract_id: string;
  perspective: ContractPerspective;
  document_scope?: AnalysisDocumentScope;
  status: AnalysisStatus;
  summary_executive: string | null;
  general_risk: RiskLevel | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface AnalysisDetail extends AnalysisSummary {
  extracted_data: Record<string, ExtractedFieldValue>;
  clauses: AnalysisClause[];
  findings: AnalysisFinding[];
  llm_metadata: Record<string, string>;
  approval: AnalysisApproval | null;
}

export interface AnalysisStatusResponse {
  id: string;
  contract_id: string;
  perspective: ContractPerspective;
  status: AnalysisStatus;
  started_at: string | null;
  completed_at: string | null;
}

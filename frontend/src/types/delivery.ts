export interface ReportSummary {
  id: string;
  analysis_id: string;
  format: 'pdf' | 'json';
  generated_by: string;
  generated_at: string;
}

export interface ChatSession {
  id: string;
  contract_id: string;
  analysis_id: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  references: Record<string, unknown>[];
  created_at: string | null;
}

export interface NotificationRecord {
  id: string;
  analysis_id: string;
  lawyer_email: string;
  decision: string;
  status: 'pending' | 'sent' | 'failed';
  sent_at: string | null;
  created_at: string;
}

export interface ReviewMessage {
  id: string;
  analysis_id: string;
  user_id: string;
  author_name: string;
  author_email: string;
  author_role: 'client' | 'lawyer' | string;
  content: string;
  created_at: string;
}

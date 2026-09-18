import { DOCUMENT_TYPE_LABELS } from '../config';
import {
  documentTypeDisplayLabel,
  FINAL_APPROVED_LAWYER_REVISION_LABEL,
} from './contractLifecycle';

describe('documentTypeDisplayLabel', () => {
  it('uses configured labels for standard document types', () => {
    expect(documentTypeDisplayLabel('main_contract')).toBe(DOCUMENT_TYPE_LABELS.main_contract);
    expect(documentTypeDisplayLabel('annex')).toBe(DOCUMENT_TYPE_LABELS.annex);
  });

  it('shows final approved copy for lawyer revision on terminated contracts', () => {
    expect(documentTypeDisplayLabel('lawyer_revision', 'terminated')).toBe(
      FINAL_APPROVED_LAWYER_REVISION_LABEL,
    );
  });

  it('keeps edited label when contract is not terminated', () => {
    expect(documentTypeDisplayLabel('lawyer_revision', 'approved')).toBe(
      DOCUMENT_TYPE_LABELS.lawyer_revision,
    );
  });

  it('falls back to raw type when unknown', () => {
    expect(documentTypeDisplayLabel('custom_type')).toBe('custom_type');
  });
});

export function documentTypeChipColor(
  documentType: string,
): 'primary' | 'secondary' | 'default' {
  if (documentType === 'main_contract') {
    return 'primary';
  }
  if (documentType === 'annex') {
    return 'secondary';
  }
  if (documentType === 'lawyer_revision') {
    return 'primary';
  }
  return 'default';
}

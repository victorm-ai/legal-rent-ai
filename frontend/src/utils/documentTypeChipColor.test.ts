import { documentTypeChipColor } from './documentTypeChipColor';

describe('documentTypeChipColor', () => {
  it('maps known document types to MUI chip colors', () => {
    expect(documentTypeChipColor('main_contract')).toBe('primary');
    expect(documentTypeChipColor('lawyer_revision')).toBe('primary');
    expect(documentTypeChipColor('annex')).toBe('secondary');
  });

  it('uses default color for unknown types', () => {
    expect(documentTypeChipColor('other')).toBe('default');
  });
});

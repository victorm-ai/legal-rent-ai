import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import type { ContractDocumentType } from '../../types/contracts';
import { documentTypeDisplayLabel } from '../../utils/contractLifecycle';
import { documentTypeChipColor } from '../../utils/documentTypeChipColor';

const DOCUMENT_TYPE_ORDER: ContractDocumentType[] = [
  'main_contract',
  'annex',
  'other',
  'lawyer_revision',
];

function sortDocumentTypes(types: string[]): string[] {
  const known = DOCUMENT_TYPE_ORDER.filter((type) => types.includes(type));
  const unknown = types.filter((type) => !DOCUMENT_TYPE_ORDER.includes(type as ContractDocumentType));
  return [...known, ...unknown];
}

interface DocumentTypeChipsProps {
  types: string[];
  size?: 'small' | 'medium';
  /** When set to `terminated`, lawyer revision chips show the final approved label. */
  contractStatus?: string | null;
}

export default function DocumentTypeChips({
  types,
  size = 'small',
  contractStatus = null,
}: DocumentTypeChipsProps) {
  const uniqueTypes = sortDocumentTypes([...new Set(types)]);

  if (uniqueTypes.length === 0) {
    return null;
  }

  return (
    <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
      {uniqueTypes.map((documentType) => (
        <Chip
          key={documentType}
          label={documentTypeDisplayLabel(documentType, contractStatus)}
          size={size}
          color={documentTypeChipColor(documentType)}
          sx={{ height: 22, fontSize: '0.7rem', fontWeight: 600 }}
        />
      ))}
    </Stack>
  );
}

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { alpha } from '@mui/material/styles';
import ChatFormattedMessage from './ChatFormattedMessage';

interface ChatReference {
  type?: string;
  title?: string;
  section?: string;
  page?: number | null;
  id?: string | null;
  code?: string;
  article?: string;
}

interface ChatMessageBubbleProps {
  role: string;
  authorLabel: string;
  content: string;
  references?: ChatReference[];
  formatReference: (ref: Record<string, unknown>) => string;
}

export default function ChatMessageBubble({
  role,
  authorLabel,
  content,
  references = [],
  formatReference,
}: ChatMessageBubbleProps) {
  const isUser = role === 'user';
  const variant = isUser ? 'user' : 'assistant';

  return (
    <Box
      sx={{
        mb: 1.5,
        p: 1.5,
        borderRadius: 1.5,
        bgcolor: (theme) =>
          isUser
            ? alpha(theme.palette.secondary.main, 0.1)
            : alpha(theme.palette.primary.main, 0.1),
        border: '1px solid',
        borderColor: (theme) =>
          isUser
            ? alpha(theme.palette.secondary.main, 0.35)
            : alpha(theme.palette.primary.main, 0.35),
        borderLeftWidth: 4,
        borderLeftColor: isUser ? 'secondary.main' : 'primary.main',
        boxShadow: isUser ? 0 : 1,
      }}
    >
      <Typography
        variant="caption"
        sx={{
          fontWeight: 700,
          color: isUser ? 'secondary.dark' : 'primary.dark',
          display: 'block',
          mb: 0.75,
        }}
      >
        {authorLabel}
      </Typography>
      <ChatFormattedMessage content={content} variant={variant} />
      {references.length > 0 && (
        <Box
          sx={{
            mt: 1.25,
            pt: 1,
            borderTop: '1px dashed',
            borderColor: 'divider',
          }}
        >
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
            Referencias ({references.length})
          </Typography>
          {references.map((ref, index) => (
            <Typography key={index} variant="caption" component="div" color="text.secondary">
              • {formatReference(ref as Record<string, unknown>)}
            </Typography>
          ))}
        </Box>
      )}
    </Box>
  );
}

import Box from '@mui/material/Box';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatFormattedMessageProps {
  content: string;
  variant?: 'assistant' | 'user';
}

export default function ChatFormattedMessage({
  content,
  variant = 'assistant',
}: ChatFormattedMessageProps) {
  const accent = variant === 'assistant' ? 'primary.main' : 'secondary.main';

  return (
    <Box
      sx={{
        color: 'text.primary',
        fontSize: '0.875rem',
        lineHeight: 1.55,
        '& p': { m: 0, mb: 1 },
        '& p:last-child': { mb: 0 },
        '& ul, & ol': { pl: 2.5, my: 1, mb: 1.25 },
        '& li': { mb: 0.5 },
        '& li::marker': {
          color: accent,
        },
        '& strong': {
          fontWeight: 700,
          color: variant === 'assistant' ? 'primary.dark' : 'text.primary',
        },
        '& em': {
          color: 'text.secondary',
        },
        '& h3, & h4': {
          fontSize: '0.95rem',
          fontWeight: 700,
          color: accent,
          mt: 1.5,
          mb: 0.75,
        },
        '& h3:first-of-type, & h4:first-of-type': { mt: 0 },
        '& blockquote': {
          m: 0,
          my: 1,
          pl: 1.5,
          borderLeft: 3,
          borderColor: accent,
          color: 'text.secondary',
        },
        '& table': {
          width: '100%',
          borderCollapse: 'collapse',
          my: 1.25,
          display: 'block',
          overflowX: 'auto',
        },
        '& thead': {
          bgcolor: 'grey.100',
        },
        '& th': {
          fontWeight: 700,
          textAlign: 'left',
          color: variant === 'assistant' ? 'primary.dark' : 'text.primary',
        },
        '& th, & td': {
          border: '1px solid',
          borderColor: 'divider',
          p: 1,
          fontSize: '0.8125rem',
          verticalAlign: 'top',
        },
        '& tbody tr:nth-of-type(even)': {
          bgcolor: 'action.hover',
        },
        '& code': {
          fontFamily: 'monospace',
          fontSize: '0.8rem',
          bgcolor: 'grey.100',
          px: 0.5,
          borderRadius: 0.5,
        },
      }}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </Box>
  );
}

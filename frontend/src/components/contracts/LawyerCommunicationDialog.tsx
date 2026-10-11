import { useCallback, useEffect, useRef, useState } from 'react';

import Alert from '@mui/material/Alert';

import Box from '@mui/material/Box';

import Button from '@mui/material/Button';

import CircularProgress from '@mui/material/CircularProgress';

import Dialog from '@mui/material/Dialog';

import DialogActions from '@mui/material/DialogActions';

import DialogContent from '@mui/material/DialogContent';

import DialogTitle from '@mui/material/DialogTitle';

import TextField from '@mui/material/TextField';

import Typography from '@mui/material/Typography';

import { ROLE_LABELS } from '../../config';

import { useAuth } from '../../context/useAuth';

import {

  getContractRequest,

  listContractReviewMessagesRequest,

  markReviewMessagesReadRequest,

  sendContractReviewMessageRequest,

} from '../../services/api';

import type { AnalysisSummary } from '../../types/analysis';

import type { ReviewMessage } from '../../types/delivery';

import ChatFormattedMessage from './ChatFormattedMessage';



interface LawyerCommunicationDialogProps {

  open: boolean;

  contractId: string | null;

  contractTitle: string | null;

  contractStatus: string | null;

  analyses: AnalysisSummary[];

  onClose: () => void;

  onMarkedRead?: () => void;

}



function reviewAuthorLabel(message: ReviewMessage, currentUserId?: string): string {

  if (message.user_id === currentUserId) {

    return 'You';

  }

  return ROLE_LABELS[message.author_role] ?? message.author_name ?? message.author_email;

}



export default function LawyerCommunicationDialog({

  open,

  contractId,

  contractTitle,

  contractStatus,

  analyses: _analyses,

  onClose,

  onMarkedRead,

}: LawyerCommunicationDialogProps) {

  const { user, getAuthHeader } = useAuth();

  const reviewMessagesContractRef = useRef<string | null>(null);

  const [reviewMessages, setReviewMessages] = useState<ReviewMessage[]>([]);

  const [reviewInput, setReviewInput] = useState('');

  const [reviewLoading, setReviewLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [liveContractStatus, setLiveContractStatus] = useState<string | null>(contractStatus);



  const isLawyer = user?.role === 'lawyer';

  const canSendReviewMessage = liveContractStatus !== null && liveContractStatus !== 'draft';

  const canSubmitReviewMessage = canSendReviewMessage && reviewInput.trim().length >= 1;

  const onMarkedReadRef = useRef(onMarkedRead);

  const wasOpenRef = useRef(false);

  onMarkedReadRef.current = onMarkedRead;



  const markMessagesReadSilently = useCallback(async () => {

    if (!contractId || !canSendReviewMessage) {

      return;

    }

    const authHeader = getAuthHeader();

    if (!authHeader) {

      return;

    }

    await markReviewMessagesReadRequest(authHeader, contractId);

  }, [canSendReviewMessage, contractId, getAuthHeader]);



  const loadReviewMessages = useCallback(async () => {

    if (!contractId) {

      return;

    }

    const authHeader = getAuthHeader();

    if (!authHeader) {

      return;

    }



    setReviewLoading(true);

    setError(null);

    const result = await listContractReviewMessagesRequest(authHeader, contractId);

    setReviewLoading(false);



    if (!result.ok) {

      setError(result.detail);

      return;

    }



    setReviewMessages(result.data);

    reviewMessagesContractRef.current = contractId;

  }, [contractId, getAuthHeader]);



  useEffect(() => {

    if (!open || !contractId) {

      return;

    }



    if (reviewMessagesContractRef.current !== contractId) {

      setReviewMessages([]);

      reviewMessagesContractRef.current = contractId;

    }

    setReviewInput('');

    setError(null);

    setLiveContractStatus(contractStatus);



    let cancelled = false;



    void (async () => {

      const authHeader = getAuthHeader();

      if (!authHeader) {

        return;

      }



      const statusResult = await getContractRequest(authHeader, contractId);

      if (!cancelled && statusResult.ok) {

        setLiveContractStatus(statusResult.data.status);

      }



      await loadReviewMessages();



      if (!cancelled) {

        const status =

          statusResult.ok && statusResult.data.status !== 'draft'

            ? statusResult.data.status

            : contractStatus;

        if (status && status !== 'draft') {

          await markReviewMessagesReadRequest(authHeader, contractId);

        }

      }

    })();



    return () => {

      cancelled = true;

    };

  }, [open, contractId, contractStatus, getAuthHeader, loadReviewMessages]);



  useEffect(() => {

    if (open) {

      wasOpenRef.current = true;

      return;

    }

    if (!wasOpenRef.current) {

      return;

    }

    onMarkedReadRef.current?.();

  }, [open]);



  const handleSendReviewMessage = async () => {

    if (!contractId || !reviewInput.trim() || !canSendReviewMessage) {

      return;

    }

    const authHeader = getAuthHeader();

    if (!authHeader) {

      return;

    }



    setReviewLoading(true);

    const result = await sendContractReviewMessageRequest(

      authHeader,

      contractId,

      reviewInput.trim(),

    );

    setReviewLoading(false);

    if (!result.ok) {

      setError(result.detail);

      return;

    }



    setReviewInput('');

    await loadReviewMessages();

    await markMessagesReadSilently();

    onMarkedReadRef.current?.();

  };



  const handleClose = () => {

    onClose();

  };



  return (

    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="md">

      <DialogTitle>

        {isLawyer ? 'Client communication' : 'Lawyer communication'}

        {contractTitle ? ` — ${contractTitle}` : ''}

      </DialogTitle>

      <DialogContent dividers>

        {error && (

          <Alert severity="error" sx={{ mb: 2 }}>

            {error}

          </Alert>

        )}



        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, minHeight: 320 }}>

          <Typography variant="body2" color="text.secondary">

            {isLawyer

              ? 'Messages from the client about this contract. Replies are saved in the case file.'

              : 'Share your decision or comments for the lawyer. Messages are saved in the case file.'}

          </Typography>

          {!canSendReviewMessage && (

            <Alert severity="info">

              {isLawyer

                ? 'The contract is still a draft; the client must send it for legal review.'

                : 'Send the contract for legal review to message the lawyer.'}

            </Alert>

          )}

          {reviewLoading && reviewMessages.length === 0 && (

            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>

              <CircularProgress size={28} />

            </Box>

          )}

          <Box sx={{ flex: 1, overflowY: 'auto', maxHeight: 360 }}>

            {reviewMessages.length === 0 && !reviewLoading && canSendReviewMessage && (

              <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>

                No messages in this thread yet.

              </Typography>

            )}

            {reviewMessages.map((message) => (

              <Box

                key={message.id}

                sx={{

                  mb: 1.5,

                  p: 1.5,

                  borderRadius: 1,

                  bgcolor: message.user_id === user?.id ? 'action.hover' : 'background.paper',

                  border: '1px solid',

                  borderColor: 'divider',

                }}

              >

                <Typography variant="caption" color="text.secondary">

                  {reviewAuthorLabel(message, user?.id)}

                  {message.created_at

                    ? ` · ${new Date(message.created_at).toLocaleString('en-US')}`

                    : ''}

                </Typography>

                <ChatFormattedMessage

                  content={message.content}

                  variant={message.user_id === user?.id ? 'user' : 'assistant'}

                />

              </Box>

            ))}

          </Box>

          {canSendReviewMessage && (

            <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>

              <TextField

                fullWidth

                multiline

                minRows={2}

                size="small"

                placeholder={

                  isLawyer

                    ? 'Write your reply to the client…'

                    : 'Write your decision or comment for the lawyer…'

                }

                value={reviewInput}

                onChange={(e) => setReviewInput(e.target.value)}

                onKeyDown={(e) => {

                  if (e.key === 'Enter' && !e.shiftKey) {

                    e.preventDefault();

                    void handleSendReviewMessage();

                  }

                }}

              />

              <Button

                variant="contained"

                onClick={() => void handleSendReviewMessage()}

                disabled={reviewLoading || !canSubmitReviewMessage}

              >

                Send

              </Button>

            </Box>

          )}

        </Box>

      </DialogContent>

      <DialogActions>

        <Button onClick={handleClose}>Close</Button>

      </DialogActions>

    </Dialog>

  );

}


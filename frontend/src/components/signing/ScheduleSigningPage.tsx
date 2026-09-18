import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Divider from '@mui/material/Divider';
import Grid from '@mui/material/Grid2';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

const WEEKDAY_HEADERS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

type ScheduleContext = {
  contract_id: string;
  contract_title: string | null;
  status: string;
  timezone: string;
  slot_minutes: number;
  open_hour: number;
  close_hour: number;
  days_ahead: number;
  bookable_dates: string[];
  slots_by_date: Record<string, string[]>;
};

function parseIsoDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function toIsoDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function addMonths(date: Date, delta: number): Date {
  return new Date(date.getFullYear(), date.getMonth() + delta, 1);
}

function formatMonthYear(date: Date): string {
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
}

function formatSelectedDay(iso: string): string {
  return parseIsoDate(iso).toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

export default function ScheduleSigningPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [context, setContext] = useState<ScheduleContext | null>(null);
  const [viewMonth, setViewMonth] = useState(() => startOfMonth(new Date()));
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [confirmMessage, setConfirmMessage] = useState<string | null>(null);

  const bookableSet = useMemo(
    () => new Set(context?.bookable_dates ?? []),
    [context?.bookable_dates],
  );

  const storageKey = useMemo(
    () => (token ? `signing-scheduled:${token.slice(0, 24)}` : ''),
    [token],
  );

  useEffect(() => {
    if (!token) {
      setError('Invalid link: missing security token.');
      setLoading(false);
      return;
    }
    if (storageKey && sessionStorage.getItem(storageKey)) {
      setConfirmed(true);
      setConfirmMessage(sessionStorage.getItem(storageKey));
    }

    const load = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/public/signing-schedule?token=${encodeURIComponent(token)}`,
        );
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.detail ?? 'Could not load scheduling data');
        }
        const data = (await response.json()) as ScheduleContext;
        setContext(data);
        const first = data.bookable_dates[0] ?? null;
        setSelectedDate(first);
        if (first && data.slots_by_date[first]?.[0]) {
          setSelectedTime(data.slots_by_date[first][0]);
        }
        if (first) {
          setViewMonth(startOfMonth(parseIsoDate(first)));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Network error');
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [token, storageKey]);

  const calendarCells = useMemo(() => {
    const year = viewMonth.getFullYear();
    const month = viewMonth.getMonth();
    const firstWeekday = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const cells: Array<{ key: string; day: number | null; iso: string | null }> = [];

    for (let i = 0; i < firstWeekday; i += 1) {
      cells.push({ key: `pad-${i}`, day: null, iso: null });
    }
    for (let day = 1; day <= daysInMonth; day += 1) {
      const iso = toIsoDate(new Date(year, month, day));
      cells.push({ key: iso, day, iso });
    }
    return cells;
  }, [viewMonth]);

  const timesForSelected = useMemo(() => {
    if (!context || !selectedDate) {
      return [];
    }
    return context.slots_by_date[selectedDate] ?? [];
  }, [context, selectedDate]);

  const slotLabel = useMemo(() => {
    if (!selectedDate || !selectedTime) {
      return '';
    }
    return `${formatSelectedDay(selectedDate)} at ${selectedTime} (Mexico City)`;
  }, [selectedDate, selectedTime]);

  const handleSelectDate = useCallback(
    (iso: string) => {
      if (!bookableSet.has(iso)) {
        return;
      }
      setSelectedDate(iso);
      const firstTime = context?.slots_by_date[iso]?.[0] ?? null;
      setSelectedTime(firstTime);
    },
    [bookableSet, context?.slots_by_date],
  );

  const handleConfirm = useCallback(async () => {
    if (!token || !slotLabel) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/public/signing-schedule/confirm?token=${encodeURIComponent(token)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ slot_label: slotLabel }),
        },
      );
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail ?? 'Could not confirm the appointment');
      }
      const data = await response.json();
      setConfirmed(true);
      setConfirmMessage(data.message as string);
      if (storageKey) {
        sessionStorage.setItem(storageKey, data.message as string);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Confirmation failed');
    } finally {
      setLoading(false);
    }
  }, [slotLabel, storageKey, token]);

  return (
    <Box sx={{ maxWidth: 960, mx: 'auto', py: 4, px: 2 }}>
      <Paper sx={{ p: { xs: 2, md: 3 }, borderRadius: 2 }}>
        <Typography variant="h5" gutterBottom fontWeight={600}>
          Schedule in-person signing
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Choose a date within the next {context?.days_ahead ?? 30} days, then a time slot (
          Mon–Fri, {context?.open_hour ?? 9}:00–{context?.close_hour ?? 18}:00 Mexico City,{' '}
          {context?.slot_minutes ?? 45}-minute blocks).
        </Typography>

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!loading && context && !confirmed && (
          <>
            <Typography variant="subtitle1" sx={{ mb: 2 }}>
              {context.contract_title ?? 'Lease contract'}
            </Typography>
            <Grid container spacing={3}>
              <Grid size={{ xs: 12, md: 5 }}>
                <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
                  <Button aria-label="Previous month" onClick={() => setViewMonth((m) => addMonths(m, -1))}>
                    ‹
                  </Button>
                  <Typography variant="subtitle1" fontWeight={600}>
                    {formatMonthYear(viewMonth)}
                  </Typography>
                  <Button aria-label="Next month" onClick={() => setViewMonth((m) => addMonths(m, 1))}>
                    ›
                  </Button>
                </Stack>
                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(7, 1fr)',
                    gap: 0.5,
                    textAlign: 'center',
                  }}
                >
                  {WEEKDAY_HEADERS.map((label) => (
                    <Typography key={label} variant="caption" color="text.secondary" fontWeight={600}>
                      {label}
                    </Typography>
                  ))}
                  {calendarCells.map((cell) => {
                    if (cell.day === null || !cell.iso) {
                      return <Box key={cell.key} sx={{ py: 1.2 }} />;
                    }
                    const bookable = bookableSet.has(cell.iso);
                    const selected = selectedDate === cell.iso;
                    return (
                      <Button
                        key={cell.key}
                        variant={selected ? 'contained' : 'text'}
                        disabled={!bookable}
                        onClick={() => handleSelectDate(cell.iso!)}
                        sx={{
                          minWidth: 0,
                          py: 1,
                          borderRadius: '50%',
                          fontWeight: selected ? 700 : 400,
                          opacity: bookable ? 1 : 0.35,
                        }}
                      >
                        {cell.day}
                      </Button>
                    );
                  })}
                </Box>
              </Grid>
              <Grid size={{ xs: 12, md: 7 }}>
                <Divider sx={{ display: { md: 'none' }, mb: 2 }} />
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  {selectedDate ? formatSelectedDay(selectedDate) : 'Select a date'}
                </Typography>
                {!selectedDate && (
                  <Typography variant="body2" color="text.secondary">
                    Pick an available day on the calendar.
                  </Typography>
                )}
                {selectedDate && timesForSelected.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    No time slots left for this day.
                  </Typography>
                )}
                <Stack spacing={1} sx={{ mt: 1, maxHeight: 320, overflow: 'auto' }}>
                  {timesForSelected.map((time) => (
                    <Button
                      key={time}
                      variant={selectedTime === time ? 'contained' : 'outlined'}
                      onClick={() => setSelectedTime(time)}
                      sx={{ justifyContent: 'center' }}
                    >
                      {time}
                    </Button>
                  ))}
                </Stack>
                <Button
                  variant="contained"
                  size="large"
                  fullWidth
                  sx={{ mt: 3 }}
                  disabled={!selectedDate || !selectedTime}
                  onClick={() => void handleConfirm()}
                >
                  Confirm appointment (simulated)
                </Button>
              </Grid>
            </Grid>
          </>
        )}

        {confirmed && confirmMessage && <Alert severity="success">{confirmMessage}</Alert>}
      </Paper>
    </Box>
  );
}

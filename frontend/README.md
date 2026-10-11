# Frontend — Legal Rent AI

SPA **React 19 + TypeScript + Vite + Material UI**. Consumes the API in `backend/` (default `http://localhost:8000`).

## Scripts

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # dist/
npm run preview
npm test         # Vitest
```

From the repo root on Windows: `start_frontend.bat` → `scripts/windows/start_frontend.bat`.

In Docker, nginx serves the build at **http://localhost:8080** with `/api` proxy to the backend.

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend base URL (in Docker Compose typically `/api` via nginx) |

Copy `frontend/.env.example` to `frontend/.env.local` to override.

## Routes (`App.tsx`)

| Route | Component | Auth |
|------|------------|------|
| `/login` | `LoginForm` | Public |
| `/dashboard` | `Dashboard` | JWT (`ProtectedRoute`) |
| `/schedule-signing` | `ScheduleSigningPage` | Query token (`?token=`), no login |

## Structure

```
src/
├── App.tsx
├── config.ts               # API base URL
├── theme.ts                # Indigo palette (MUI); role-based theme
├── context/
│   └── AuthContext.tsx     # JWT session (localStorage)
├── services/               # HTTP client (incl. SSE chat)
├── types/
└── components/
    ├── auth/               # Login, ProtectedRoute, RootRedirect
    ├── layout/             # Header, Footer
    ├── dashboard/          # Main dashboard
    ├── login/
    ├── signing/            # ScheduleSigningPage (public schedule)
    └── contracts/          # Upload, analysis, chat, comparison, closure
        ├── UploadContractDialog.tsx
        ├── AnalysisResultsDialog.tsx
        ├── DocumentViewerDialog.tsx
        ├── RevisionComparisonDialog.tsx
        ├── CompareContractsDialog.tsx
        ├── LawyerCommunicationDialog.tsx
        ├── ContractClosureDialog.tsx
        ├── ContractStatusSelect.tsx
        ├── DeleteContractDialog.tsx
        └── ChatMessageBubble.tsx / ChatFormattedMessage.tsx
```

## API-connected functionality

- Authentication (`/auth/*`)
- Contract listing and creation (multipart)
- Document viewing and extracted text
- Analysis and status polling
- Chat with **SSE streaming** (`POST /chat/sessions/{id}/messages/stream`)
- Reports and downloads (incl. download tokens)
- Contract comparison and edited revision
- Client–lawyer messages, notifications, and RF-56 states
- Case closure (`approved` → `terminated`) and post-email flow to signing schedule

## Notes

- The backend must be running (`python run_backend.py` from the repo root).
- UI in **English**; product documentation in English in `docs/`.
- If the project is on **Dropbox**, exclude `node_modules/` from sync before `npm install`.

## Documentation

- [REST API](../docs/api.md)
- [Root README](../README.md)

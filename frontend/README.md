# Frontend — Legal Rent AI

SPA **React 19 + TypeScript + Vite + Material UI**. Consume la API en `backend/` (por defecto `http://localhost:8000`).

## Scripts

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # dist/
npm run preview
npm test         # Vitest
```

Desde la raíz del repo en Windows: `start_frontend.bat` → `scripts/windows/start_frontend.bat`.

En Docker, nginx sirve el build en **http://localhost:8080** con proxy `/api` al backend.

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend base URL (en Docker Compose suele ser `/api` vía nginx) |

Copia `frontend/.env.example` a `frontend/.env.local` para override.

## Rutas (`App.tsx`)

| Ruta | Componente | Auth |
|------|------------|------|
| `/login` | `LoginForm` | Pública |
| `/dashboard` | `Dashboard` | JWT (`ProtectedRoute`) |
| `/schedule-signing` | `ScheduleSigningPage` | Token en query (`?token=`), sin login |

## Estructura

```
src/
├── App.tsx
├── config.ts               # API base URL
├── theme.ts                # Paleta indigo (MUI); tema por rol
├── context/
│   └── AuthContext.tsx     # Sesión JWT (localStorage)
├── services/               # Cliente HTTP (incl. SSE chat)
├── types/
└── components/
    ├── auth/               # Login, ProtectedRoute, RootRedirect
    ├── layout/             # Header, Footer
    ├── dashboard/          # Dashboard principal
    ├── login/
    ├── signing/            # ScheduleSigningPage (agenda pública)
    └── contracts/          # Upload, análisis, chat, comparación, cierre
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

## Funcionalidad conectada a la API

- Autenticación (`/auth/*`)
- Listado y alta de contratos (multipart)
- Visualización de documentos y texto extraído
- Análisis y polling de status
- Chat con **streaming SSE** (`POST /chat/sessions/{id}/messages/stream`)
- Reportes y descargas (incl. tokens de descarga)
- Comparación entre contratos y revisión editada
- Mensajes cliente–abogado, notificaciones y estados RF-56
- Cierre del expediente (`approved` → `terminated`) y flujo post-correo hacia agenda de firma

## Notas

- El backend debe estar en marcha (`python run_backend.py` desde la raíz del repo).
- UI en **inglés**; documentación del producto en español en `docs/`.
- Si el proyecto está en **Dropbox**, excluir `node_modules/` de la sincronización antes de `npm install`.

## Documentación

- [API REST](../docs/api.md)
- [README raíz](../README.md)

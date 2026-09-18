# Corregir error `DomainNotLinked` (correo ACS)

Cuando el abogado usa **Marcar como Terminado**, el agente intenta enviar correo real por Azure. Si aparece:

```text
(DomainNotLinked) The specified sender domain has not been linked.
```

significa que **faltan dos cosas en Azure** (no es un bug de LangGraph):

1. **Vincular** el dominio de email al recurso Communication Services.
2. Poner en `.env` el **MailFrom real** (`donotreply@….azurecomm.net`), no `DoNotReply@legalrentai.local`.

El contrato **no queda terminado** (hay rollback a `approved`).

---

## Paso 1 — Dominio en Email Communication Service

1. [Portal Azure](https://portal.azure.com) → grupo **`Dev-Kanbanboard-app`**.
2. Abre **`kanban-email-service`** (Email Communication Service).
3. Menú **Provision domains** / **Domains**.
4. Si no hay dominio: **Add domain** → **Azure managed domain** (nombre típico del recurso: `AzureManagedDomain`).
5. Espera estado **Verified** / listo para enviar.
6. Dominio de este proyecto (FQDN):
   - `1994c775-bd8e-439f-9132-a444ad76b9b4.azurecomm.net` (sin `.us1`; confirmar en `az communication email domain show`)
7. MailFrom en `.env`:
   - `DoNotReply@1994c775-bd8e-439f-9132-a444ad76b9b4.azurecomm.net`

---

## Paso 2 — Conectar dominio al Communication Service

1. Abre **`kanban-communication-service`** (Communication Services) en el mismo grupo de recursos.
2. Menú **Email** → **Domains**.
3. **Connect domain**.
4. Elige suscripción, **`Dev-Kanbanboard-app`**, **`kanban-email-service`**, dominio verificado cuyo FQDN sea `1994c775-bd8e-439f-9132-a444ad76b9b4.us1.azurecomm.net` (recurso en portal a menudo `AzureManagedDomain`).
5. Confirma. Debe aparecer en la lista de dominios conectados.

> Communication Service y Email Service deben estar en la **misma región geográfica** (p. ej. United States).

---

## Paso 3 — Actualizar `.env` local

En la raíz del repo:

```env
AZURE_COMMUNICATION_SENDER_ADDRESS=donotreply@TU-GUID.azurecomm.net
NOTIFICATION_DEV_MODE=false
```

(`AZURE_COMMUNICATION_CONNECTION_STRING` ya apunta a `kanban-communication-service`.)

Reinicia el backend: `python run_backend.py`.

---

## Paso 4 — Probar

```powershell
python scripts/azure/probe_acs_email_sender.py code.zemoreno@gmail.com
```

Debe imprimir `OK`. Luego repite **Marcar como Terminado** en la UI.

---

## Desde tu PC con Azure CLI (recomendado)

Guía completa: [link-domain-local-cli.md](./link-domain-local-cli.md)

Resumen:

```powershell
az login --tenant "01ea369a-621c-4b70-a22c-b9c52c2076d4" --scope "https://management.core.windows.net//.default"
.\scripts\windows\link_acs_email_domain.ps1
python scripts/azure/probe_acs_email_sender.py code.zemoreno@gmail.com
```

---

## Qué pasó cuando intentamos automatizar desde aquí

- El remitente en `.env` era un **placeholder** (`.local`).
- Azure exige dominio **conectado** + MailFrom **real**.
- No se pudo entrar al portal desde el entorno del agente; la corrección es **en Azure + `.env`**, como arriba.

Referencia Microsoft: [Connect a verified email domain](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/email/connect-email-communication-resource).

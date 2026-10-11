# Fix `DomainNotLinked` error (ACS email)

When the lawyer uses **Mark as Terminated**, the agent tries to send real email via Azure. If you see:

```text
(DomainNotLinked) The specified sender domain has not been linked.
```

**two things are missing in Azure** (not a LangGraph bug):

1. **Link** the email domain to the Communication Services resource.
2. Set the **real MailFrom** in `.env` (`donotreply@….azurecomm.net`), not `DoNotReply@legalrentai.local`.

The contract **is not terminated** (rollback to `approved`).

---

## Step 1 — Domain in Email Communication Service

1. [Azure Portal](https://portal.azure.com) → group **`Dev-Kanbanboard-app`**.
2. Open **`kanban-email-service`** (Email Communication Service).
3. Menu **Provision domains** / **Domains**.
4. If no domain: **Add domain** → **Azure managed domain** (typical resource name: `AzureManagedDomain`).
5. Wait for **Verified** / ready to send.
6. Domain for this project (FQDN):
   - `1994c775-bd8e-439f-9132-a444ad76b9b4.azurecomm.net` (without `.us1`; confirm with `az communication email domain show`)
7. MailFrom in `.env`:
   - `DoNotReply@1994c775-bd8e-439f-9132-a444ad76b9b4.azurecomm.net`

---

## Step 2 — Connect domain to Communication Service

1. Open **`kanban-communication-service`** (Communication Services) in the same resource group.
2. Menu **Email** → **Domains**.
3. **Connect domain**.
4. Choose subscription, **`Dev-Kanbanboard-app`**, **`kanban-email-service`**, verified domain whose FQDN is `1994c775-bd8e-439f-9132-a444ad76b9b4.us1.azurecomm.net` (portal resource often named `AzureManagedDomain`).
5. Confirm. It should appear in the connected domains list.

> Communication Service and Email Service must be in the **same geographic region** (e.g. United States).

---

## Step 3 — Update local `.env`

At repo root:

```env
AZURE_COMMUNICATION_SENDER_ADDRESS=donotreply@YOUR-GUID.azurecomm.net
NOTIFICATION_DEV_MODE=false
```

(`AZURE_COMMUNICATION_CONNECTION_STRING` already points to `kanban-communication-service`.)

Restart the backend: `python run_backend.py`.

---

## Step 4 — Test

```powershell
python scripts/azure/probe_acs_email_sender.py code.zemoreno@gmail.com
```

Should print `OK`. Then retry **Mark as Terminated** in the UI.

---

## From your PC with Azure CLI (recommended)

Full guide: [link-domain-local-cli.md](./link-domain-local-cli.md)

Summary:

```powershell
az login --tenant "01ea369a-621c-4b70-a22c-b9c52c2076d4" --scope "https://management.core.windows.net//.default"
.\scripts\windows\link_acs_email_domain.ps1
python scripts/azure/probe_acs_email_sender.py code.zemoreno@gmail.com
```

---

## What happened when we tried to automate from here

- The sender in `.env` was a **placeholder** (`.local`).
- Azure requires a **connected** domain + **real** MailFrom.
- Portal access was not available from the agent environment; the fix is **in Azure + `.env`**, as above.

Microsoft reference: [Connect a verified email domain](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/email/connect-email-communication-resource).

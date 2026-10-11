# Azure — resources and scope

Documentation **without secrets**. Credentials live in `secrets/azure.local.env` (local, gitignored).

## Resource groups

| Group | Purpose |
|-------|-----|
| `Dev-Kanbanboard-app` | **Azure Communication Services** already provisioned (`kanban-communication-service`, `kanban-email-service`). The backend uses the connection string for signing coordination agent emails. |
| `lidr` | **Legal Rent AI on Azure**: ACR `legalrentlidracr` (eastus2), Azure SQL `legalrentlidr-sql` (centralus), Container Apps `legalrent-lidr-api` + `legalrent-lidr-web`. Script: `scripts/azure/deploy-lidr.ps1`. |

Email resources **do not** need to move to `lidr`: the app in `lidr` can consume ACS from the other group via connection string in application configuration.

## Variables used by the API (`.env` / App Service)

- `AZURE_COMMUNICATION_CONNECTION_STRING`
- `AZURE_COMMUNICATION_SENDER_ADDRESS` (verified domain in ACS Email)
- `NOTIFICATION_DEV_MODE=false` for real sending (configured in local `.env`)
- `pip install -e .` includes `azure-communication-email`

### Link domain ↔ Communication Service

If ACS returns **`DomainNotLinked`**, in Azure Portal:

1. **Email Communication Service** resource (`kanban-email-service`) → **Provision domains** / Azure managed domain.
2. Copy **MailFrom** (`donotreply@….azurecomm.net`) to `AZURE_COMMUNICATION_SENDER_ADDRESS`.
3. In **Communication Services** (`kanban-communication-service`) → **Email** → connect the domain from step 1.

Local test: `python scripts/azure/probe_acs_email_sender.py code.zemoreno@gmail.com`

Detailed guide if contract closure fails: [fix-domain-not-linked.md](./fix-domain-not-linked.md)

## Authentication

- Development: portal or `az login`.
- Recommended production: **Managed Identity** or **service principal**, not portal user/password on the server.

## Local Docker

Before App Service, validate the app with [docker.md](./docker.md) (`docker compose`).

## Reference

- [Azure Communication Services Email](https://learn.microsoft.com/azure/communication-services/concepts/email/email-overview)

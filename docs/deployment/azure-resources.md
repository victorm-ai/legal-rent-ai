# Azure — recursos y alcance

Documentación **sin secretos**. Credenciales en `secrets/azure.local.env` (local, gitignored).

## Grupos de recursos

| Grupo | Uso |
|-------|-----|
| `Dev-Kanbanboard-app` | **Azure Communication Services** ya provisionado (`kanban-communication-service`, `kanban-email-service`). El backend usa el connection string para correos del agente de coordinación de firma. |
| `lidr` | **Legal Rent AI en Azure**: ACR `legalrentlidracr` (eastus2), Azure SQL `legalrentlidr-sql` (centralus), Container Apps `legalrent-lidr-api` + `legalrent-lidr-web`. Script: `scripts/azure/deploy-lidr.ps1`. |

Los recursos de correo **no** tienen que moverse a `lidr`: la app en `lidr` puede consumir ACS del otro grupo vía connection string en configuración de la aplicación.

## Variables que usa la API (`.env` / App Service)

- `AZURE_COMMUNICATION_CONNECTION_STRING`
- `AZURE_COMMUNICATION_SENDER_ADDRESS` (dominio verificado en ACS Email)
- `NOTIFICATION_DEV_MODE=false` para envío real (configurado en `.env` local)
- `pip install -e .` incluye `azure-communication-email`

### Enlace dominio ↔ Communication Service

Si ACS responde **`DomainNotLinked`**, en Portal Azure:

1. Recurso **Email Communication Service** (`kanban-email-service`) → **Provision domains** / dominio Azure managed.
2. Copia el **MailFrom** (`donotreply@….azurecomm.net`) a `AZURE_COMMUNICATION_SENDER_ADDRESS`.
3. En **Communication Services** (`kanban-communication-service`) → **Email** → conecta el dominio del paso 1.

Prueba local: `python scripts/azure/probe_acs_email_sender.py code.zemoreno@gmail.com`

Guía detallada si falla el cierre del contrato: [fix-domain-not-linked.md](./fix-domain-not-linked.md)

## Autenticación

- Desarrollo: portal o `az login`.
- Producción recomendada: **Managed Identity** o **service principal**, no usuario/contraseña del portal en el servidor.

## Docker local

Antes de App Service, validar la app con [docker.md](./docker.md) (`docker compose`).

## Referencia

- [Azure Communication Services Email](https://learn.microsoft.com/azure/communication-services/concepts/email/email-overview)

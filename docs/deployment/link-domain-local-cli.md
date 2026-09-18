# Vincular dominio ACS desde tu PC (Azure CLI)

Sí: puedes corregir **`DomainNotLinked`** en local con **Azure CLI** + login interactivo (no hace falta entrar al portal si prefieres terminal).

## 1. Azure CLI

Si no lo tienes:

```powershell
winget install -e --id Microsoft.AzureCLI
```

Cierra y abre PowerShell para que reconozca `az`.

## 2. Login (management)

A veces `az account show` funciona pero los comandos de **Communication** piden un token con scope de **management**. Ejecuta:

```powershell
az logout
az login --tenant "01ea369a-621c-4b70-a22c-b9c52c2076d4" --scope "https://management.core.windows.net//.default"
```

Alternativa con código en el navegador:

```powershell
az login --tenant "01ea369a-621c-4b70-a22c-b9c52c2076d4" --scope "https://management.core.windows.net//.default" --use-device-code
```

Abre https://login.microsoft.com/device e introduce el código que muestra la terminal.

Usa la cuenta que tenga acceso al grupo **`Dev-Kanbanboard-app`**.

## 3. Extensión communication

```powershell
az extension add --name communication --yes
```

## 4. Enlazar dominio (automático)

Desde la raíz del repo:

```powershell
.\scripts\windows\link_acs_email_domain.ps1
```

El script:

- Lista dominios de **`kanban-email-service`**
- Busca el FQDN `1994c775-bd8e-439f-9132-a444ad76b9b4.us1.azurecomm.net`
- Ejecuta `az communication update` en **`kanban-communication-service`**

## 5. Verificar envío

```powershell
python scripts/azure/probe_acs_email_sender.py code.zemoreno@gmail.com
```

Debe imprimir `OK`. Reinicia el backend y prueba **Marcar como Terminado**.

## 6. Comando manual (si el script falla)

Sustituye `{subscription-id}` y confirma el nombre del recurso dominio (a menudo `AzureManagedDomain`):

```powershell
az communication update `
  --resource-group Dev-Kanbanboard-app `
  --name kanban-communication-service `
  --linked-domains "/subscriptions/{subscription-id}/resourceGroups/Dev-Kanbanboard-app/providers/Microsoft.Communication/emailServices/kanban-email-service/domains/AzureManagedDomain"
```

## Errores frecuentes

| Error | Qué hacer |
|-------|-----------|
| `AADSTS9002313` / invalid request | Repetir `az login` con el `--scope` de management (paso 2). |
| `Authorization failed` | Tu usuario no tiene rol en `Dev-Kanbanboard-app`; pide Contributor en el RG. |
| Sigue `DomainNotLinked` tras el script | Comprueba `az communication show ... --query properties.linkedDomains` no esté vacío. |

Referencia: [Connect email domain](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/email/connect-email-communication-resource).

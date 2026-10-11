# Link ACS domain from your PC (Azure CLI)

Yes: you can fix **`DomainNotLinked`** locally with **Azure CLI** + interactive login (no portal required if you prefer the terminal).

## 1. Azure CLI

If you do not have it:

```powershell
winget install -e --id Microsoft.AzureCLI
```

Close and reopen PowerShell so it recognizes `az`.

## 2. Login (management)

Sometimes `az account show` works but **Communication** commands need a token with **management** scope. Run:

```powershell
az logout
az login --tenant "01ea369a-621c-4b70-a22c-b9c52c2076d4" --scope "https://management.core.windows.net//.default"
```

Alternative with browser code:

```powershell
az login --tenant "01ea369a-621c-4b70-a22c-b9c52c2076d4" --scope "https://management.core.windows.net//.default" --use-device-code
```

Open https://login.microsoft.com/device and enter the code shown in the terminal.

Use the account that has access to group **`Dev-Kanbanboard-app`**.

## 3. Communication extension

```powershell
az extension add --name communication --yes
```

## 4. Link domain (automated)

From repo root:

```powershell
.\scripts\windows\link_acs_email_domain.ps1
```

The script:

- Lists domains for **`kanban-email-service`**
- Finds FQDN `1994c775-bd8e-439f-9132-a444ad76b9b4.us1.azurecomm.net`
- Runs `az communication update` on **`kanban-communication-service`**

## 5. Verify sending

```powershell
python scripts/azure/probe_acs_email_sender.py code.zemoreno@gmail.com
```

Should print `OK`. Restart the backend and test **Mark as Terminated**.

## 6. Manual command (if the script fails)

Replace `{subscription-id}` and confirm the domain resource name (often `AzureManagedDomain`):

```powershell
az communication update `
  --resource-group Dev-Kanbanboard-app `
  --name kanban-communication-service `
  --linked-domains "/subscriptions/{subscription-id}/resourceGroups/Dev-Kanbanboard-app/providers/Microsoft.Communication/emailServices/kanban-email-service/domains/AzureManagedDomain"
```

## Common errors

| Error | What to do |
|-------|-----------|
| `AADSTS9002313` / invalid request | Repeat `az login` with management `--scope` (step 2). |
| `Authorization failed` | Your user lacks a role on `Dev-Kanbanboard-app`; request Contributor on the RG. |
| Still `DomainNotLinked` after script | Check `az communication show ... --query properties.linkedDomains` is not empty. |

Reference: [Connect email domain](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/email/connect-email-communication-resource).

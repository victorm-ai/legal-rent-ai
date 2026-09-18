# Vincula el dominio de kanban-email-service a kanban-communication-service (corrige DomainNotLinked).
# Requisito: sesión Azure con permiso en Dev-Kanbanboard-app
#
# Uso:
#   1) az login   (o el login con scope de management; ver docs/deployment/link-domain-local-cli.md)
#   2) .\scripts\windows\link_acs_email_domain.ps1

$ErrorActionPreference = "Stop"

$resourceGroup = "Dev-Kanbanboard-app"
$communicationService = "kanban-communication-service"
$emailService = "kanban-email-service"
$expectedDomainFqdn = "1994c775-bd8e-439f-9132-a444ad76b9b4.azurecomm.net"

$az = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
if (-not (Test-Path $az)) {
    $az = (Get-Command az -ErrorAction SilentlyContinue).Source
}
if (-not $az) {
    Write-Host "Instala Azure CLI: winget install -e --id Microsoft.AzureCLI"
    exit 1
}

Write-Host "Comprobando extension 'communication'..."
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $az extension add --name communication --yes 2>&1 | Out-Null
$ErrorActionPreference = $prevEap

$subId = (& $az account show --query id -o tsv 2>$null)
if (-not $subId) {
    Write-Host "No hay sesion. Ejecuta:"
    Write-Host '  az login --tenant "01ea369a-621c-4b70-a22c-b9c52c2076d4" --scope "https://management.core.windows.net//.default"'
    exit 1
}

Write-Host "Suscripcion: $subId"
Write-Host "Listando dominios en $emailService ..."
$domainsJson = & $az communication email domain list `
    --email-service-name $emailService `
    --resource-group $resourceGroup `
    -o json
$domains = $domainsJson | ConvertFrom-Json

if (-not $domains -or $domains.Count -eq 0) {
    Write-Host "No hay dominios. Provisiona Azure Managed Domain en kanban-email-service primero."
    exit 1
}

$domainName = $null
foreach ($d in $domains) {
    $fqdn = $d.properties.mailFromSenderDomain
    if (-not $fqdn) { $fqdn = $d.properties.fromSenderDomain }
    Write-Host "  - recurso: $($d.name)  FQDN: $fqdn"
    if ($fqdn -eq $expectedDomainFqdn) {
        $domainName = $d.name
    }
}
if (-not $domainName) {
    $domainName = $domains[0].name
    Write-Host "Usando primer dominio: $domainName"
} else {
    Write-Host "Dominio objetivo: $domainName ($expectedDomainFqdn)"
}

$linkedDomain = "/subscriptions/$subId/resourceGroups/$resourceGroup/providers/Microsoft.Communication/emailServices/$emailService/domains/$domainName"

Write-Host ""
Write-Host "Dominios enlazados actuales en $communicationService :"
& $az communication show --name $communicationService --resource-group $resourceGroup --query "properties.linkedDomains" -o json

Write-Host ""
Write-Host "Vinculando:"
Write-Host $linkedDomain

& $az communication update `
    --resource-group $resourceGroup `
    --name $communicationService `
    --linked-domains $linkedDomain

Write-Host ""
Write-Host "Dominios enlazados despues del update:"
& $az communication show --name $communicationService --resource-group $resourceGroup --query "properties.linkedDomains" -o json

Write-Host ""
Write-Host "Prueba: python scripts/azure/probe_acs_email_sender.py code.zemoreno@gmail.com"

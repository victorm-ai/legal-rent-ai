# Build/run Compose from a non-Dropbox copy (Docker cannot read Dropbox reparse points).
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ComposeArgs = @("up", "--build")
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Dest = Join-Path $env:TEMP "legalrent-docker-build"

Write-Host "Syncing project to $Dest (hydrates Dropbox files for Docker)..."
if (Test-Path $Dest) {
    Remove-Item -Recurse -Force $Dest
}
New-Item -ItemType Directory -Path $Dest -Force | Out-Null

$robocopyArgs = @(
    $Root,
    $Dest,
    "/MIR",
    "/XD", "node_modules", "venv", ".venv", ".git", "backend\storage", "frontend\node_modules", "frontend\dist", "evals\runs", "secrets",
    "/XF", "*.pyc",
    "/NFL", "/NDL", "/NJH", "/NJS", "/nc", "/np"
)
& robocopy @robocopyArgs | Out-Null
$rc = $LASTEXITCODE
if ($rc -ge 8) {
    Write-Error "robocopy failed with exit code $rc"
}

$env:LEGALRENT_BUILD_CONTEXT = $Dest
Write-Host "LEGALRENT_BUILD_CONTEXT=$Dest"
Write-Host "Running: docker compose $($ComposeArgs -join ' ')"

Push-Location $Root
try {
    & docker compose @ComposeArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}

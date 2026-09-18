# Point Docker Desktop data (WSL VHDX + vm-data) to D:\Docker files
# Run once before the first docker compose up after a clean Docker install.
$ErrorActionPreference = "Stop"

$DockerRoot = "D:\Docker files"
$WslDir = Join-Path $DockerRoot "wsl"
$VmDataDir = Join-Path $DockerRoot "vm-data"

New-Item -ItemType Directory -Path $WslDir, $VmDataDir -Force | Out-Null

Write-Host "Stopping Docker Desktop..."
docker desktop stop 2>$null
Get-Process -Name "Docker Desktop","com.docker.backend","com.docker.build","docker-desktop" -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
wsl --shutdown
Start-Sleep -Seconds 2

$storePath = Join-Path $env:APPDATA "Docker\settings-store.json"
$legacyPath = Join-Path $env:APPDATA "Docker\settings.json"

if (-not (Test-Path $storePath)) {
    Write-Error "Docker settings not found. Install/start Docker Desktop once, then run this script again."
}

$store = Get-Content $storePath -Raw | ConvertFrom-Json
$store.CustomWslDistroDir = $WslDir
$store.DataFolder = $VmDataDir
$store | ConvertTo-Json -Depth 20 | Set-Content -Path $storePath -Encoding UTF8

if (Test-Path $legacyPath) {
    $legacy = Get-Content $legacyPath -Raw | ConvertFrom-Json
    $legacy.customWslDistroDir = $WslDir
    $legacy.dataFolder = $VmDataDir
    $legacy | ConvertTo-Json -Depth 20 | Set-Content -Path $legacyPath -Encoding UTF8
}

Write-Host "Configured:"
Write-Host "  CustomWslDistroDir -> $WslDir"
Write-Host "  DataFolder         -> $VmDataDir"
Write-Host ""
Write-Host "Start Docker Desktop, wait until it is running, then from the project root:"
Write-Host "  docker compose up --build"

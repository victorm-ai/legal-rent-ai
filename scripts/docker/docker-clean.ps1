# Remove Legal Rent AI compose stack (containers, volumes, locally built images).
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $Root
try {
    docker compose down -v --rmi local --remove-orphans
    docker rmi mcr.microsoft.com/mssql/server:2022-latest 2>$null
    docker builder prune -af
    $temp = Join-Path $env:TEMP "legalrent-docker-build"
    if (Test-Path $temp) {
        Remove-Item -Recurse -Force $temp
    }
    docker system df
}
finally {
    Pop-Location
}

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Push-Location $PSScriptRoot
try {
    & (Join-Path $PSScriptRoot 'Initialize.ps1')

    $envPath = Join-Path $PSScriptRoot '.env'
    & docker compose --env-file $envPath up -d
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up -d ist mit Exitcode $LASTEXITCODE fehlgeschlagen."
    }
}
finally {
    Pop-Location
}

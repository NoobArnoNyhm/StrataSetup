$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Push-Location $PSScriptRoot
try {
    if (-not (Test-Path -LiteralPath '.env')) {
        Copy-Item -LiteralPath '.env.example' -Destination '.env'
    }

    $envPath = Join-Path $PSScriptRoot '.env'
    $text = [System.IO.File]::ReadAllText($envPath)
    $keyPattern = '(?m)^STRATA_API_KEY=([^\r\n]*)'
    $keyMatches = [regex]::Matches($text, $keyPattern)
    if ($keyMatches.Count -ne 1) {
        throw '.env muss genau eine Zeile STRATA_API_KEY= enthalten.'
    }
    $key = $keyMatches[0].Groups[1].Value.Trim().Trim("'", '"')
    if ($key.Length -eq 0) {
        $bytes = New-Object byte[] 32
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try {
            $rng.GetBytes($bytes)
        }
        finally {
            $rng.Dispose()
        }
        $key = [BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
        $text = [regex]::Replace($text, $keyPattern, "STRATA_API_KEY=$key")
        [System.IO.File]::WriteAllText($envPath, $text, (New-Object System.Text.UTF8Encoding($false)))
        Write-Host 'Zufaelligen API-Key in .env gespeichert (wird nicht ausgegeben).'
    }
    elseif ($key.Length -lt 16) {
        throw 'STRATA_API_KEY muss mindestens 16 Zeichen enthalten.'
    }

    $json = & docker compose --env-file $envPath config --format json --no-path-resolution
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker-Compose-Konfiguration ist ungueltig.'
    }
    $config = ($json -join "`n") | ConvertFrom-Json
    $effectiveKey = $config.services.strata.environment.API_KEY
    if ($effectiveKey.Length -lt 16) {
        throw 'Der effektive API-Key ist zu kurz. Auch Prozess-Umgebungsvariablen pruefen.'
    }

    $mounts = @($config.services.strata.volumes) + @($config.services.'pi-dev'.volumes)
    foreach ($mount in $mounts) {
        $source = $mount.source
        if ($source -notmatch '^[A-Za-z]:[\\/]') {
            throw "Absoluter Windows-Pfad fuer Bind-Mount erwartet: $source"
        }
        if ($mount.target -eq '/workspace') {
            if (-not (Test-Path -LiteralPath $source -PathType Container)) {
                throw "Der Workspace existiert nicht: $source"
            }
        }
        else {
            New-Item -ItemType Directory -Path $source -Force | Out-Null
        }
        Write-Host "Bind-Mount vorbereitet: $source"
    }

    $memory = & docker info --format '{{.MemTotal}}'
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker-Daemon ist nicht erreichbar.'
    }
    if ([long]$memory -lt 46GB) {
        Write-Warning 'Docker sieht weniger als 46 GiB RAM. Vor dem IQ2_XS-Modellstart WSL2-RAM pruefen; empfohlen sind zunaechst 48 GB. WSL wird nicht automatisch veraendert.'
    }
    Write-Host 'Initialisierung abgeschlossen. Es wurden keine Container gestartet.'
}
finally {
    Pop-Location
}

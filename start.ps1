$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = Join-Path $Root ".venv313\Scripts\python.exe"
$Frontend = Join-Path $Root "frontend"
$Logs = Join-Path $Root "logs"

if (-not (Test-Path $Python)) {
    throw "Python virtual environment not found: $Python"
}

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "[setup] Installing frontend dependencies..."
    Push-Location $Frontend
    try {
        & npm.cmd install
    } finally {
        Pop-Location
    }
}

New-Item -ItemType Directory -Force -Path $Logs | Out-Null

function Test-LocalPort([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(350)) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Wait-LocalPort([int]$Port, [int]$Seconds = 30) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-LocalPort $Port) {
            return $true
        }
        Start-Sleep -Milliseconds 450
    }
    return $false
}

if (-not (Test-LocalPort 8000)) {
    Write-Host "[start] FastAPI -> http://127.0.0.1:8000"
    $backend = Start-Process `
        -FilePath $Python `
        -ArgumentList "run.py" `
        -WorkingDirectory (Join-Path $Root "backend") `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $Logs "backend.log") `
        -RedirectStandardError (Join-Path $Logs "backend.error.log") `
        -PassThru
    Write-Host "[start] backend pid: $($backend.Id)"
}

if (-not (Test-LocalPort 5173)) {
    Write-Host "[start] Vue -> http://127.0.0.1:5173"
    $frontendProcess = Start-Process `
        -FilePath "npm.cmd" `
        -ArgumentList "run", "dev", "--", "--host", "127.0.0.1" `
        -WorkingDirectory $Frontend `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $Logs "frontend.log") `
        -RedirectStandardError (Join-Path $Logs "frontend.error.log") `
        -PassThru
    Write-Host "[start] frontend pid: $($frontendProcess.Id)"
}

if (-not (Wait-LocalPort 8000 30)) {
    throw "FastAPI did not start. Check logs\backend.error.log"
}

if (-not (Wait-LocalPort 5173 30)) {
    throw "Vite did not start. Check logs\frontend.error.log"
}

Write-Host ""
Write-Host "Minecraft Link is ready: http://127.0.0.1:5173"
Write-Host "API: http://127.0.0.1:8000"
Write-Host "Docs: $Root\docs\api.md"
Write-Host "Logs: $Logs"

Start-Process "http://127.0.0.1:5173"

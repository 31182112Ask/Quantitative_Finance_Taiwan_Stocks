param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$OutLog = Join-Path $Root "ui_server.log"
$ErrLog = Join-Path $Root "ui_server.err.log"
$StrategyUrl = "http://${HostName}:${Port}/strategy"
$BenchmarkUrl = "http://${HostName}:${Port}/benchmark"

function Test-PortInUse {
    param([int]$LocalPort)
    $connection = Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    return $null -ne $connection
}

function Wait-UiReady {
    param([string]$Url)
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

Set-Location $Root

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python was not found in PATH." -ForegroundColor Red
    exit 1
}

if (Test-PortInUse -LocalPort $Port) {
    Write-Host "Port $Port is already in use. Close the existing UI server first." -ForegroundColor Yellow
    exit 2
}

Remove-Item -LiteralPath $OutLog, $ErrLog -Force -ErrorAction SilentlyContinue

$server = Start-Process `
    -FilePath "python" `
    -ArgumentList @("-m", "src.cli", "ui", "--host", $HostName, "--port", [string]$Port) `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -PassThru `
    -WindowStyle Hidden

try {
    if (-not (Wait-UiReady -Url $StrategyUrl)) {
        Write-Host "UI server did not become ready. See $ErrLog" -ForegroundColor Red
        exit 3
    }

    Write-Host ""
    Write-Host "tw_quant_intraday UI is running." -ForegroundColor Green
    Write-Host "Strategy:  $StrategyUrl"
    Write-Host "Benchmark: $BenchmarkUrl"
    Write-Host "Server PID: $($server.Id)"
    Write-Host ""

    if ($env:TW_QUANT_OPEN_BROWSER -ne "0") {
        Start-Process $StrategyUrl | Out-Null
    }

    if ($env:TW_QUANT_SMOKE -eq "1") {
        Start-Sleep -Seconds 2
    } else {
        Read-Host "Press Enter to stop the UI server"
    }
}
finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 300
        Write-Host "UI server stopped." -ForegroundColor Green
    }
}

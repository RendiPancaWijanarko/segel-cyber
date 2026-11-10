<#
.SYNOPSIS
    Preflight verification for SEGEL AI Inspector and local Ollama daemon.
.DESCRIPTION
    Checks whether Ollama is reachable at 127.0.0.1:11434, verifies model qwen3:4b
    is downloaded and ready, dispatches a warm-up inference request with keep_alive=30m,
    and prints measured inference latency along with `ollama ps` process status.
    Exits with a non-zero exit code if any check fails.
#>

[CmdletBinding()]
param(
    [string]$Endpoint = "http://127.0.0.1:11434",
    [string]$Model = "qwen3:4b"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SEGEL AI Inspector Preflight Check                        " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Target Endpoint : $Endpoint"
Write-Host "Target Model    : $Model"
Write-Host ""

# 1. Connectivity Check to 127.0.0.1:11434
Write-Host "[1/4] Checking Ollama loopback connectivity..." -NoNewline
try {
    $tagsUri = "$Endpoint/api/tags"
    $tagsResp = Invoke-RestMethod -Uri $tagsUri -Method Get -TimeoutSec 5
    Write-Host " [OK]" -ForegroundColor Green
}
catch {
    Write-Host " [FAILED]" -ForegroundColor Red
    Write-Error "ERROR: Unable to connect to Ollama daemon at $Endpoint.`nPlease ensure the Ollama service is running (e.g., run 'ollama serve' in background)."
    exit 1
}

# 2. Model Verification Check
Write-Host "[2/4] Verifying presence of model '$Model'..." -NoNewline
$modelFound = $false
$modelDigest = ""
if ($tagsResp.models) {
    foreach ($m in $tagsResp.models) {
        if ($m.name -eq $Model -or $m.model -eq $Model -or $m.name -like "$Model*") {
            $modelFound = $true
            $modelDigest = $m.digest
            break
        }
    }
}

if (-not $modelFound) {
    Write-Host " [FAILED]" -ForegroundColor Red
    Write-Error "ERROR: Model '$Model' is not present in local Ollama repository.`nPlease pull the model by executing: ollama pull $Model"
    exit 2
}
Write-Host " [OK]" -ForegroundColor Green
Write-Host "      Model Digest: $modelDigest" -ForegroundColor Gray

# 3. Warm-up Inference Request (keep_alive=30m)
Write-Host "[3/4] Sending warm-up request (keep_alive 30m)..." -NoNewline
$warmupPayload = @{
    model = $Model
    messages = @(
        @{
            role = "user"
            content = "Ping: warm up memory and context."
        }
    )
    stream = $false
    keep_alive = "30m"
    options = @{
        num_predict = 10
        temperature = 0
    }
} | ConvertTo-Json -Depth 5

try {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $chatUri = "$Endpoint/api/chat"
    $chatResp = Invoke-RestMethod -Uri $chatUri -Method Post -Body $warmupPayload -ContentType "application/json; charset=utf-8" -TimeoutSec 60
    $sw.Stop()
    Write-Host " [OK]" -ForegroundColor Green
    $latencyMs = $sw.ElapsedMilliseconds
    $latencySec = [Math]::Round($sw.Elapsed.TotalSeconds, 3)
    Write-Host "      Warm-up Latency: $latencyMs ms ($latencySec s)" -ForegroundColor Yellow
}
catch {
    Write-Host " [FAILED]" -ForegroundColor Red
    Write-Error "ERROR: Warm-up request to $Model failed: $_"
    exit 3
}

# 4. Print Ollama Running Process Status
Write-Host "[4/4] Querying 'ollama ps' status..." -ForegroundColor Green
try {
    $psOutput = & ollama ps 2>&1
    if ($LASTEXITCODE -eq 0) {
        $psOutput | ForEach-Object { Write-Host "      $_" -ForegroundColor Cyan }
    } else {
        Write-Host "      Warning: 'ollama ps' command returned non-zero exit code ($LASTEXITCODE)." -ForegroundColor Yellow
    }
}
catch {
    Write-Host "      Notice: Unable to execute 'ollama ps' directly ($_); daemon is operational via HTTP API." -ForegroundColor Gray
}

Write-Host ""
Write-Host "Preflight check completed successfully: AI Inspector is ready." -ForegroundColor Green
Write-Host ""
exit 0

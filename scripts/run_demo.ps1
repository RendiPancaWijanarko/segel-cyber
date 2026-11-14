<#
.SYNOPSIS
    Starts the SEGEL Release Desk Web Application.
.DESCRIPTION
    Launches FastAPI Release Desk with configurable AI subsystem state (SEGEL_AI_ENABLED=1 or 0),
    setting environment variables and outputting the local server URL.
.PARAMETER AiEnabled
    Switch or integer (1 or 0) determining whether the AI Inspector subsystem is enabled. Default is 1.
.PARAMETER Port
    Port to bind Uvicorn server to. Default is 8000.
.PARAMETER Host
    Host address to bind to. Default is 127.0.0.1 (loopback).
#>

[CmdletBinding()]
param(
    [ValidateSet("0", "1", "false", "true")]
    [string]$AiEnabled = "1",
    [int]$Port = 8000,
    [string]$HostAddress = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$aiFlag = if ($AiEnabled -in @("1", "true")) { "1" } else { "0" }
$env:SEGEL_AI_ENABLED = $aiFlag
$env:SEGEL_AI_ENDPOINT = "http://127.0.0.1:11434"
$env:SEGEL_AI_MODEL = "qwen3:4b"
$env:SEGEL_AI_TIMEOUT_S = "30"

$aiStatusText = if ($aiFlag -eq "1") { "ENABLED (Ollama qwen3:4b loopback)" } else { "DISABLED (Deterministic Policy Engine only)" }

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SEGEL Release Desk — Secure Configuration Distribution    " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Server URL       : http://${HostAddress}:${Port}" -ForegroundColor Green
Write-Host "AI Subsystem     : $aiStatusText" -ForegroundColor Yellow
Write-Host "Local Host       : $HostAddress"
Write-Host "Port             : $Port"
Write-Host ""
Write-Host "Press Ctrl+C to stop the Release Desk web application." -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Ensure src/ is in PYTHONPATH for clean module resolution
$repoRoot = Split-Path -Parent $PSScriptRoot
$srcPath = Join-Path $repoRoot "src"
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$srcPath;" + $env:PYTHONPATH
} else {
    $env:PYTHONPATH = "$srcPath"
}

# Locate python executable in current virtual environment (compatible with PS 5.1 and PS Core)
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

& $pythonExe -m uvicorn release_desk.app:app --app-dir "$srcPath" --host $HostAddress --port $Port

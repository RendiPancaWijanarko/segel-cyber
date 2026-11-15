# ==============================================================================
# SEGEL — Peluncur Demonstrasi Otomatis Layar Penuh (Autopilot Demo Launcher)
# Kartika Cyber Hackathon 2026 — PUSSIBERAD TNI AD & CODEPOLITAN
# ==============================================================================

[CmdletBinding()]
param(
    [switch]$AiEnabled = $true,
    [int]$Port = 8000,
    [switch]$AppMode = $true
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  SEGEL &bull; PELUNCUR DEMONSTRASI OTOMATIS TERINKRONISASI OBS" -ForegroundColor Yellow
Write-Host "  Sistem Edar Gelar Elektronik Lapis-ganda (PUSSIBERAD TNI AD)" -ForegroundColor White
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""

# 1. Konfigurasi Variabel Lingkungan AI
if ($AiEnabled) {
    $env:SEGEL_AI_ENABLED = "1"
    Write-Host "[+] Mode AI Penasihat: DIAKTIFKAN (SEGEL_AI_ENABLED=1)" -ForegroundColor Cyan
} else {
    $env:SEGEL_AI_ENABLED = "0"
    Write-Host "[!] Mode AI Penasihat: DINONAKTIFKAN (SEGEL_AI_ENABLED=0)" -ForegroundColor Yellow
}

$targetUrl = "http://127.0.0.1:$Port/"

# 2. Periksa apakah server Release Desk sudah berjalan
$serverRunning = $false
try {
    $res = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/healthz" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($res.StatusCode -eq 200) {
        $serverRunning = $true
    }
} catch {
    $serverRunning = $false
}

if (-not $serverRunning) {
    Write-Host "[*] Memulai server Release Desk di latar belakang (Port $Port)..." -ForegroundColor White
    $pythonExe = ".\.venv\Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) {
        $pythonExe = "python"
    }

    $serverProcess = Start-Process -FilePath $pythonExe -ArgumentList "-m uvicorn src.release_desk.app:app --host 127.0.0.1 --port $Port" -PassThru
    Start-Sleep -Seconds 3

    # Verifikasi konektivitas
    $ready = $false
    for ($i = 0; $i -lt 10; $i++) {
        try {
            $check = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/healthz" -UseBasicParsing -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($check.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    if ($ready) {
        Write-Host "[OK] Server Release Desk aktif dan merespons pada $targetUrl" -ForegroundColor Green
    } else {
        Write-Warning "Server belum merespons cepat, tetap mencoba membuka antarmuka..."
    }
} else {
    Write-Host "[OK] Server Release Desk telah berjalan pada port $Port." -ForegroundColor Green
}

# Reset state demo agar bersih dari awal (0 stempel, 0 rilis)
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:$Port/reset" -Method Post -TimeoutSec 2 | Out-Null
    Write-Host "[OK] Status demo berhasil di-reset ke kondisi awal (0 rilis, buku besar bersih)." -ForegroundColor Green
} catch {
    Write-Warning "Gagal menghubungi endpoint reset."
}

# 3. Luncurkan Peramban dalam Mode Aplikasi Bersih (App Mode / Fullscreen)
Write-Host ""
Write-Host "[*] Meluncurkan Demonstrasi Otomatis pada peramban..." -ForegroundColor Cyan

$edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edgePath)) {
    $edgePath = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
}

if ($AppMode -and (Test-Path $edgePath)) {
    # Buka Edge dalam mode App tanpa tab/toolbar (bersih untuk OBS)
    Start-Process -FilePath $edgePath -ArgumentList "--app=`"$targetUrl`" --start-maximized"
} else {
    Start-Process $targetUrl
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Yellow
Write-Host "  PETUNJUK PEREKAMAN VIDEO DENGAN OBS STUDIO:" -ForegroundColor White
Write-Host "==================================================================" -ForegroundColor Yellow
Write-Host "  1. Buka OBS Studio -> Tambahkan Source: Window Capture (Jendela SEGEL)." -ForegroundColor White
Write-Host "  2. Posisikan webcam talking head Anda di pojok layar." -ForegroundColor White
Write-Host "  3. Klik jendela SEGEL di browser (http://127.0.0.1:8000), lalu tekan tombol [SPASI]." -ForegroundColor Cyan
Write-Host "  4. Demonstrasi otomatis langsung berjalan di antarmuka asli:" -ForegroundColor Green
Write-Host "     - Membuka terminal otomatis: cek Ollama, model Qwen3:4b, latensi, dan 437 uji lolos." -ForegroundColor Green
Write-Host "     - Menyorot metrik dasbor utama secara interaktif." -ForegroundColor Green
Write-Host "     - Mengisi form rilis baru, alur 5-stempel, gelar canary, dan promosi paspor." -ForegroundColor Green
Write-Host "     - Menampilkan kasus DEV-14 dengan panel AI Advisory." -ForegroundColor Green
Write-Host ""
Write-Host "  Tombol Pintas (Hotkeys):" -ForegroundColor White
Write-Host "  - [Spasi]       : Memulai / Jeda demonstrasi" -ForegroundColor Gray
Write-Host "  - [Escape]      : Hentikan dan reset demonstrasi" -ForegroundColor Gray
Write-Host "==================================================================" -ForegroundColor Yellow
Write-Host ""

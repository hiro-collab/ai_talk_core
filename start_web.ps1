[CmdletBinding()]
param(
    [switch]$Sync,
    [switch]$NoOpen,
    [switch]$SkipDoctor
)

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

function Test-LocalCommand {
    param([Parameter(Mandatory = $true)][string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-LocalCommand "uv")) {
    throw "uv is not available in PATH. Install uv first, then rerun this script."
}

if (-not (Test-LocalCommand "ffmpeg")) {
    Write-Warning "ffmpeg is not available in PATH. File and microphone transcription will fail until ffmpeg is installed."
}

if ($Sync -or -not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Syncing Python environment..."
    & uv sync
}

if (-not $SkipDoctor) {
    Write-Host "Runtime check..."
    & uv run python -m src.main --doctor
}

$url = "http://127.0.0.1:8000"

if (-not $NoOpen) {
    Start-Job -ScriptBlock {
        param([string]$TargetUrl)
        for ($i = 0; $i -lt 40; $i++) {
            try {
                Invoke-WebRequest -UseBasicParsing -Uri $TargetUrl -TimeoutSec 1 | Out-Null
                Start-Process $TargetUrl
                return
            } catch {
                Start-Sleep -Milliseconds 500
            }
        }
        Start-Process $TargetUrl
    } -ArgumentList $url | Out-Null
}

Write-Host "Starting ai_core Web UI at $url"
Write-Host "Press Ctrl+C to stop the server."
& uv run python -m src.web.app

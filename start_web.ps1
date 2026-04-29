[CmdletBinding()]
param(
    [switch]$Sync,
    [switch]$NoOpen,
    [switch]$SkipDoctor,
    [string]$Preset = $env:AI_TALK_CORE_WEB_PRESET,
    [string]$Token = $env:AI_TALK_CORE_WEB_TOKEN,
    [string]$RuntimeStatusFile = "",
    [string]$Query = ""
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

$projectPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if ($Sync -or -not (Test-Path $projectPython)) {
    if ($Sync) {
        Write-Warning "uv sync may replace a machine-local CUDA Torch wheel. Rerun setup_gpu_windows.ps1 after sync if GPU transcription is needed."
    }
    Write-Host "Syncing Python environment..."
    & uv sync
}

if (-not (Test-Path $projectPython)) {
    throw "Project Python was not found at $projectPython after uv sync."
}

if (-not $SkipDoctor) {
    Write-Host "Runtime check..."
    & $projectPython -m src.main --doctor
}

$url = "http://127.0.0.1:8000"
$queryParts = @()

if ($null -eq $Preset) {
    $Preset = ""
}
$webPreset = $Preset.Trim()
if ($webPreset) {
    $env:AI_TALK_CORE_WEB_PRESET = $webPreset
    $queryParts += "profile=$([System.Uri]::EscapeDataString($webPreset))"
}

if ($null -eq $Token) {
    $Token = ""
}
$webToken = $Token.Trim()
if ($webToken) {
    $env:AI_TALK_CORE_WEB_TOKEN = $webToken
}

if ($null -eq $Query) {
    $Query = ""
}
$extraQuery = $Query.Trim()
while ($extraQuery.StartsWith("?") -or $extraQuery.StartsWith("&")) {
    $extraQuery = $extraQuery.Substring(1)
}
if ($extraQuery) {
    $queryParts += $extraQuery
}

if ($queryParts.Count -gt 0) {
    $url = "$url?$($queryParts -join '&')"
}

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
$webArgs = @("-m", "src.web.app")
if ($RuntimeStatusFile.Trim()) {
    $webArgs += @("--runtime-status-file", $RuntimeStatusFile.Trim())
}
& $projectPython @webArgs

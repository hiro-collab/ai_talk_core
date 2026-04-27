[CmdletBinding()]
param(
    [ValidateSet("cu128", "cu126", "cu118", "cpu")]
    [string]$Cuda = "cu128",
    [switch]$SkipSync
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

$projectPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-LocalCommand "nvidia-smi") -and $Cuda -ne "cpu") {
    Write-Warning "nvidia-smi is not available. CUDA Torch can still be installed, but GPU verification may fail."
}

if (-not $SkipSync -and -not (Test-Path $projectPython)) {
    Write-Host "Syncing Python environment..."
    & uv sync
}

if (-not (Test-Path $projectPython)) {
    throw "Project Python was not found at $projectPython. Run uv sync first, or rerun this script without -SkipSync."
}

$indexUrl = "https://download.pytorch.org/whl/$Cuda"

Write-Host "Installing project-local Torch build from $indexUrl"
& uv pip install --upgrade torch --index-url $indexUrl

Write-Host "Restoring project dependency floor for setuptools..."
& uv pip install --upgrade "setuptools>=82.0.1"

Write-Host "Verifying Torch runtime..."
& $projectPython -c "import torch; print('torch_version=', torch.__version__); print('torch_cuda_version=', torch.version.cuda); print('torch_cuda_available=', torch.cuda.is_available()); print('torch_device=', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')"

Write-Host "Full project diagnosis:"
& $projectPython -m src.main --doctor

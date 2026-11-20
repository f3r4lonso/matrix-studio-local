param(
    [string]$Python = 'python',
    [string]$ComfyDir = '',
    [switch]$UseExistingComfy,
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$config = Get-Content -LiteralPath (Join-Path $projectRoot 'infrastructure.json') -Raw | ConvertFrom-Json
. (Join-Path $projectRoot 'QwenImageLocal/paths.ps1')
if (!$ComfyDir) { $ComfyDir = (Get-MatrixRuntimePaths).comfy_engine }
if ($PlanOnly) {
    Write-Output ('Python required: ' + $config.python)
    Write-Output ('ComfyUI commit: ' + $config.comfyui.commit)
    Write-Output ('Torch: ' + $config.torch + ' / ' + $config.torch_index)
    $config.nodes | ForEach-Object { Write-Output ($_.name + ': ' + $_.commit) }
    Write-Output 'No downloads or changes were made.'
    exit 0
}
foreach ($command in @('git', 'curl.exe', $Python)) {
    if (!(Get-Command $command -ErrorAction SilentlyContinue)) { throw "Missing command: $command" }
}
$pythonVersion = & $Python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
if ($LASTEXITCODE -ne 0 -or $pythonVersion -ne $config.python) { throw 'Use a Python 3.12 executable with -Python.' }
function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $Program" }
}
function Get-PinnedRepository {
    param([string]$Url, [string]$Commit, [string]$Destination)
    if (!(Test-Path -LiteralPath $Destination)) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
        Invoke-Checked 'git' @('clone', '--filter=blob:none', $Url, $Destination)
        Invoke-Checked 'git' @('-C', $Destination, 'checkout', '--detach', $Commit)
    } else {
        $head = & git -C $Destination rev-parse HEAD
        if ($LASTEXITCODE -ne 0 -or $head -ne $Commit) {
            throw 'An existing checkout has a different version. Use a new directory; existing work is not overwritten.'
        }
    }
}
if (!$UseExistingComfy) { Get-PinnedRepository $config.comfyui.url $config.comfyui.commit $ComfyDir }
elseif (!(Test-Path -LiteralPath (Join-Path $ComfyDir 'main.py'))) { throw 'Existing ComfyUI main.py not found.' }
$venvPython = Join-Path $ComfyDir 'venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $venvPython)) { Invoke-Checked $Python @('-m', 'venv', (Join-Path $ComfyDir 'venv')) }
Invoke-Checked $venvPython @('-m', 'pip', 'install', '--upgrade', 'pip')
Invoke-Checked $venvPython @('-m', 'pip', 'install', ('torch==' + $config.torch), ('torchvision==' + $config.torchvision), '--index-url', $config.torch_index)
$constraints = Join-Path $projectRoot 'requirements-engine.constraints.txt'
Invoke-Checked $venvPython @('-m', 'pip', 'install', '-r', (Join-Path $ComfyDir 'requirements.txt'), '-c', $constraints)
foreach ($node in $config.nodes) {
    $destination = Join-Path $ComfyDir ('custom_nodes/' + $node.name)
    Get-PinnedRepository $node.url $node.commit $destination
    $requirements = Join-Path $destination 'requirements.txt'
    if (Test-Path -LiteralPath $requirements) { Invoke-Checked $venvPython @('-m', 'pip', 'install', '-r', $requirements, '-c', $constraints) }
}
Invoke-Checked $venvPython @('-m', 'pip', 'install', '-r', (Join-Path $projectRoot 'requirements.txt'), '-r', (Join-Path $projectRoot 'MatrixStudio/requirements-video.txt'), '-c', $constraints)
Invoke-Checked $venvPython @((Join-Path $PSScriptRoot 'configure_models.py'), '--comfy-dir', $ComfyDir)
Invoke-Checked $venvPython @('-c', 'import torch; print("CUDA available:", torch.cuda.is_available()); print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")')
Write-Output 'Infrastructure installed. Model weights are separate; see README.md.'
if ($UseExistingComfy) { Write-Output 'Existing installation reused; its compatibility must be checked.' }

param([string]$Uv = '', [switch]$PlanOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$forgeRoot = Join-Path $projectRoot 'Data/Engines/Forge'
$runtimeRoot = Join-Path $projectRoot 'Runtime/Forge'
$sourceCommit = 'db117cb2ac33f6a11ec281ff71ffd4cd02b2f05a'
$sourceUrl = 'https://github.com/Haoming02/sd-webui-forge-classic.git'
if ($PlanOnly) {
    Write-Output "Forge Neo: $sourceCommit"
    Write-Output 'Python 3.13.12; torch 2.14.1+cu130; torchvision 0.29.1+cu130; separate virtual environment.'
    Write-Output 'Requires uv and git. Shared Data/Models; no model downloads. Nothing changed.'
    exit 0
}
if (!$Uv) {
    $Uv = Join-Path $projectRoot 'Data/Assets/uv/uv.exe'
    if (!(Test-Path -LiteralPath $Uv)) {
        $command = Get-Command uv.exe -ErrorAction SilentlyContinue
        if (!$command) { throw 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ or pass -Uv with its executable path.' }
        $Uv = $command.Source
    }
}
function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $Program" }
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $forgeRoot), $runtimeRoot | Out-Null
if (!(Test-Path -LiteralPath $forgeRoot)) {
    Invoke-Checked 'git' @('clone','--branch','neo','--single-branch',$sourceUrl,$forgeRoot)
    Invoke-Checked 'git' @('-C',$forgeRoot,'checkout','--detach',$sourceCommit)
} else {
    $head = & git -C $forgeRoot rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $head -ne $sourceCommit) { throw 'Existing Forge checkout has a different version; it was not overwritten.' }
}
$pythonRoot = Join-Path $projectRoot 'Data/Assets/Python'
$env:UV_CACHE_DIR = Join-Path $projectRoot 'Data/Assets/uv/cache'
Invoke-Checked $Uv @('python','install','3.13.12','--install-dir',$pythonRoot,'--no-bin','--no-registry')
$python = Join-Path $pythonRoot 'cpython-3.13.12-windows-x86_64-none/python.exe'
$venv = Join-Path $forgeRoot 'venv'
$venvPython = Join-Path $venv 'Scripts/python.exe'
if (!(Test-Path -LiteralPath $venvPython)) { Invoke-Checked $Uv @('venv',$venv,'--python',$python,'--seed') }
$requirementsProfile = Join-Path $runtimeRoot 'requirements.compat.txt'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'requirements-forge.compat.txt') -Destination $requirementsProfile
Invoke-Checked $Uv @('pip','install','--python',$venvPython,'torch==2.14.1+cu130','torchvision==0.29.1+cu130','--index-url','https://download.pytorch.org/whl/cu130')
Invoke-Checked $Uv @('pip','install','--python',$venvPython,'-r',$requirementsProfile,'gradio==4.40.0','gradio_rangeslider==0.0.8')
Invoke-Checked $Uv @('pip','check','--python',$venvPython)
# Record uv's actual location so the launcher's --uv flag also works with -Uv.
$Uv | Set-Content -LiteralPath (Join-Path $runtimeRoot 'uv-path.txt') -Encoding utf8
Write-Output 'Forge installed. Run Abrir Forge.cmd, then refresh engines in Matrix Studio.'

param([string]$ComfyDir = '', [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $projectRoot 'QwenImageLocal/paths.ps1')
if (!$ComfyDir) { $ComfyDir = (Get-MatrixRuntimePaths).comfy_engine }
$venvPython = Join-Path $ComfyDir 'venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $venvPython)) { throw 'Run scripts/setup-local.ps1 first or pass -ComfyDir.' }
$env:MATRIX_STUDIO_COMFY_DIR = $ComfyDir
$env:MATRIX_STUDIO_COMFY_PYTHON = $venvPython
if (!$env:MATRIX_STUDIO_DATA_DIR) { $env:MATRIX_STUDIO_DATA_DIR = Join-Path $projectRoot 'Runtime' }
$server = Join-Path $projectRoot 'MatrixStudio/server.py'
if ($NoBrowser) { & $venvPython $server --no-browser } else { & $venvPython $server }
exit $LASTEXITCODE

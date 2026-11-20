$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$forgeRoot = Join-Path $projectRoot 'Data/Engines/Forge'
$runtimeRoot = Join-Path $projectRoot 'Runtime/Forge'
$forgePython = Join-Path $forgeRoot 'venv/Scripts/python.exe'
$requirementsProfile = Join-Path $runtimeRoot 'requirements.compat.txt'
$pidFile = Join-Path $runtimeRoot 'forge.pid'
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
try {
    $models = Invoke-RestMethod -Uri 'http://127.0.0.1:7860/sdapi/v1/sd-models' -TimeoutSec 3
    Write-Output 'Forge ya esta conectado: http://127.0.0.1:7860'
    exit 0
} catch {}
if (Test-Path -LiteralPath $pidFile) {
    $forgeProcessId = [int](Get-Content -LiteralPath $pidFile -Raw)
    if (Get-Process -Id $forgeProcessId -ErrorAction SilentlyContinue) {
        Write-Output 'Forge esta arrancando. Consulta Runtime/Forge/stderr.log y stdout.log.'
        exit 0
    }
}
if (!(Test-Path -LiteralPath $forgePython) -or !(Test-Path -LiteralPath $requirementsProfile)) {
    throw 'Falta instalar el entorno de Forge o su perfil de dependencias.'
}
$uvDirectory = Join-Path $projectRoot 'Data/Assets/uv'
$uvPathFile = Join-Path $runtimeRoot 'uv-path.txt'
if (Test-Path -LiteralPath $uvPathFile) {
    $uvDirectory = Split-Path -Parent ((Get-Content -LiteralPath $uvPathFile -Raw).Trim())
}
$env:PATH = $uvDirectory + ';' + $env:PATH
$env:VIRTUAL_ENV = Join-Path $forgeRoot 'venv'
$env:UV_CACHE_DIR = Join-Path $projectRoot 'Data/Assets/uv/cache'
$env:REQS_FILE = $requirementsProfile
$env:HF_HOME = Join-Path $projectRoot 'Data/Assets/HuggingFace'
$env:TORCH_HOME = Join-Path $projectRoot 'Data/Assets/TorchCache'
$env:GRADIO_ANALYTICS_ENABLED = 'False'
$env:WEBUI_LAUNCH_LIVE_OUTPUT = '1'
$forgeArguments = @(
    (Join-Path $forgeRoot 'launch.py'), '--api', '--port', '7860', '--uv',
    '--data-dir', $runtimeRoot, '--model-ref', (Join-Path $projectRoot 'Data/Models'),
    '--ckpt-dirs', (Join-Path $projectRoot 'Data/Models/StableDiffusion'),
    '--lora-dirs', (Join-Path $projectRoot 'Data/Models/Lora'),
    '--vae-dirs', (Join-Path $projectRoot 'Data/Models/VAE'),
    '--text-encoder-dirs', (Join-Path $projectRoot 'Data/Models/TextEncoders'),
    '--use-pytorch-cross-attention', '--reserve-vram', '1'
)
# Start-Process joins arguments on Windows; quote complete paths explicitly.
$quotedArguments = ($forgeArguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
$process = Start-Process -FilePath $forgePython -ArgumentList $quotedArguments -WorkingDirectory $forgeRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeRoot 'stdout.log') -RedirectStandardError (Join-Path $runtimeRoot 'stderr.log')
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
Write-Output 'Forge iniciandose en http://127.0.0.1:7860 con los modelos del proyecto.'

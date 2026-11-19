$ErrorActionPreference = 'Stop'
$port = 1235
$url = "http://127.0.0.1:$port/"
try {
    $response = Invoke-WebRequest -Uri $url -TimeoutSec 2
    if ($response.StatusCode -eq 200 -and $response.Content -match 'stable-diffusion') {
        Write-Host "La interfaz ya esta abierta: $url"
        exit 0
    }
} catch { }
$projectRoot = Split-Path -Parent $PSScriptRoot
$model = if ($env:MATRIX_STUDIO_QWEN_MODEL) { $env:MATRIX_STUDIO_QWEN_MODEL } else { Join-Path $projectRoot 'Data/Models/Qwen/model.gguf' }
$encoder = if ($env:MATRIX_STUDIO_QWEN_ENCODER) { $env:MATRIX_STUDIO_QWEN_ENCODER } else { Join-Path $projectRoot 'Data/Models/Qwen/encoder.gguf' }
$vae = if ($env:MATRIX_STUDIO_QWEN_VAE) { $env:MATRIX_STUDIO_QWEN_VAE } else { Join-Path $projectRoot 'Data/Models/Qwen/vae.safetensors' }
$cuda = if ($env:MATRIX_STUDIO_CUDA_DIR) { $env:MATRIX_STUDIO_CUDA_DIR } else { Join-Path $PSScriptRoot 'engine' }
foreach ($file in @($model, $encoder, $vae, "$cuda\cudart64_12.dll")) {
    if (!(Test-Path -LiteralPath $file)) { throw "No se encuentra: $file" }
}
$savedPath = $env:PATH
try {
    $env:PATH = "$cuda;$savedPath"
    Write-Host "Abre $url cuando el servidor termine de cargar."
    Write-Host 'Manten esta ventana abierta. Pulsa Ctrl+C para detener el servidor.'
    $serverArgs = @(
        '--listen-ip', '127.0.0.1', '--listen-port', "$port",
        '--diffusion-model', $model, '--llm', $encoder, '--vae', $vae,
        '--steps', '8', '--cfg-scale', '1', '--sampling-method', 'euler',
        '--sigmas', '1.0,0.978453,0.95418,0.926626,0.89508,0.845148,0.704534,0.414568,0.0',
        '--width', '512', '--height', '512', '--seed', '-1',
        '--backend', 'cuda0', '--max-vram', '6', '--mmap',
        '--flash-attn', 'on', '--vae-tiling'
    )
    & (Join-Path $PSScriptRoot 'engine\sd-server.exe') @serverArgs
    if ($LASTEXITCODE -ne 0) { throw "El servidor ha terminado con codigo $LASTEXITCODE." }
} finally {
    $env:PATH = $savedPath
}

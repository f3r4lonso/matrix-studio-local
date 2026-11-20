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
. (Join-Path $PSScriptRoot 'paths.ps1')
$runtimePaths = Get-MatrixRuntimePaths
$model = $runtimePaths.qwen_model
$encoder = $runtimePaths.qwen_encoder
$vae = $runtimePaths.qwen_vae
$cuda = $runtimePaths.cuda_runtime
foreach ($file in @($model, $encoder, $vae, "$cuda\cudart64_12.dll")) {
    if (!(Test-Path -LiteralPath $file)) { throw "No se encuentra: $file" }
}
$engineExecutable = if ($env:MATRIX_STUDIO_QWEN_SERVER) { $env:MATRIX_STUDIO_QWEN_SERVER } else { Join-Path $runtimePaths.sd_cpp_engine 'sd-server.exe' }
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
    & $engineExecutable @serverArgs
    if ($LASTEXITCODE -ne 0) { throw "El servidor ha terminado con codigo $LASTEXITCODE." }
} finally {
    $env:PATH = $savedPath
}

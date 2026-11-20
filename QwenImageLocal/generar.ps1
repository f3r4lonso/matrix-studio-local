param(
    [string]$Prompt = 'A small red panda sitting in a sunlit bamboo forest, detailed illustration, warm natural colors',
    [ValidateRange(256,2048)][int]$Width = 512,
    [ValidateRange(256,2048)][int]$Height = 512,
    [int]$Seed = 42
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'paths.ps1')
$runtimePaths = Get-MatrixRuntimePaths
$model = $runtimePaths.qwen_model
$encoder = $runtimePaths.qwen_encoder
$vae = $runtimePaths.qwen_vae
$cuda = $runtimePaths.cuda_runtime
foreach ($file in @($model, $encoder, $vae, "$cuda\cudart64_12.dll")) {
    if (!(Test-Path -LiteralPath $file)) { throw "No se encuentra: $file" }
}
if (($Width % 32) -ne 0 -or ($Height % 32) -ne 0) { throw 'Las dimensiones deben ser multiplos de 32.' }
$outputDir = Join-Path $PSScriptRoot 'outputs'
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$output = Join-Path $outputDir "$stamp.png"
$log = Join-Path $outputDir "$stamp.log"
$engineExecutable = if ($env:MATRIX_STUDIO_QWEN_CLI) { $env:MATRIX_STUDIO_QWEN_CLI } else { Join-Path $runtimePaths.sd_cpp_engine 'sd-cli.exe' }
$savedPath = $env:PATH
try {
    $env:PATH = "$cuda;$savedPath"
    $sdArgs = @(
        '--diffusion-model', $model, '--llm', $encoder, '--vae', $vae,
        '--prompt', $Prompt, '--steps', '8', '--cfg-scale', '1',
        '--sampling-method', 'euler',
        '--sigmas', '1.0,0.978453,0.95418,0.926626,0.89508,0.845148,0.704534,0.414568,0.0',
        '--width', "$Width", '--height', "$Height", '--seed', "$Seed",
        '--backend', 'cuda0', '--max-vram', '6', '--mmap',
        '--flash-attn', 'on', '--vae-tiling', '--output', $output
    )
    & $engineExecutable @sdArgs 2>&1 | Tee-Object -FilePath $log
    if ($LASTEXITCODE -ne 0) { throw "La generacion ha fallado (codigo $LASTEXITCODE). Registro: $log" }
    if (!(Test-Path -LiteralPath $output)) { throw "No se ha creado la imagen. Registro: $log" }
    Write-Host "Imagen guardada: $output"
} finally {
    $env:PATH = $savedPath
}

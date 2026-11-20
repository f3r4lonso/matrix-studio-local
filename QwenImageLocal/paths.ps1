function Get-MatrixRuntimePaths {
    $runtimeProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    $values = @{}
    foreach ($relative in @('config/runtime-paths.example.json', 'Data/runtime-paths.json')) {
        $path = Join-Path $runtimeProjectRoot $relative
        if (Test-Path -LiteralPath $path) {
            $parsed = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
            foreach ($property in $parsed.PSObject.Properties) { $values[$property.Name] = $property.Value }
        }
    }
    $legacy = @{ comfy_engine='Data/Packages/ComfyUI'; sd_cpp_engine='QwenImageLocal/engine'; cuda_runtime='QwenImageLocal/engine'; qwen_model='Data/Models/Qwen/model.gguf'; qwen_encoder='Data/Models/Qwen/encoder.gguf'; qwen_vae='Data/Models/Qwen/vae.safetensors' }
    $overrides = @{ comfy_engine='MATRIX_STUDIO_COMFY_DIR'; cuda_runtime='MATRIX_STUDIO_CUDA_DIR'; qwen_model='MATRIX_STUDIO_QWEN_MODEL'; qwen_encoder='MATRIX_STUDIO_QWEN_ENCODER'; qwen_vae='MATRIX_STUDIO_QWEN_VAE' }
    $resolved = @{ Root = $runtimeProjectRoot }
    foreach ($key in $legacy.Keys) {
        $value = $values[$key]
        if (!(Test-Path -LiteralPath (Join-Path $runtimeProjectRoot 'Data/runtime-paths.json'))) {
            if (!(Test-Path -LiteralPath (Join-Path $runtimeProjectRoot $value)) -and (Test-Path -LiteralPath (Join-Path $runtimeProjectRoot $legacy[$key]))) { $value = $legacy[$key] }
        }
        if ($overrides.ContainsKey($key)) {
            $override = [Environment]::GetEnvironmentVariable($overrides[$key])
            if ($override) { $value = $override }
        }
        if ([string]::IsNullOrWhiteSpace($value)) { throw "Missing runtime path: $key" }
        if (![IO.Path]::IsPathRooted($value)) { $value = Join-Path $runtimeProjectRoot $value }
        $resolved[$key] = [IO.Path]::GetFullPath($value)
    }
    [pscustomobject]$resolved
}

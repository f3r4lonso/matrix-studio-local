$ErrorActionPreference = 'Stop'
try {
    Write-Host 'Qwen Image 2.1 Turbo - generacion local'
    Write-Host 'Cierra el modelo cargado en LM Studio para liberar memoria.'
    $description = Read-Host 'Describe la imagen (mejor en ingles)'
    if ([string]::IsNullOrWhiteSpace($description)) { throw 'Escribe una descripcion.' }
    & (Join-Path $PSScriptRoot 'generar.ps1') -Prompt $description
} catch {
    Write-Host $_ -ForegroundColor Red
} finally {
    Read-Host 'Pulsa Intro para cerrar'
}

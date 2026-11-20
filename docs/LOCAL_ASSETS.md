# Motores y modelos locales

Las instalaciones nuevas agrupan los motores en `Data/Engines` y los pesos en `Data/Models`. Ambos directorios quedan fuera de Git.

```text
Data/
  Engines/
    ComfyUI/                 # motor, nodos personalizados y venv
    StableDiffusionCpp/      # sd-cli.exe, sd-server.exe y DLL del motor opcional
    CUDA12/                  # DLL CUDA compatibles con ese build de sd.cpp
  Models/
    StableDiffusion/         # checkpoints SD 1.5 y SDXL
    DiffusionModels/         # modelos de difusión separados (Qwen, Wan, etc.)
    TextEncoders/            # codificadores
    VAE/                    # VAE de la arquitectura correspondiente
    Lora/                   # LoRAs; deben coincidir con la familia del modelo
    AnimateDiff/            # modelos de movimiento
    AnimateDiffMotionLora/   # LoRAs de movimiento
  runtime-paths.json         # configuración privada generada localmente
  matrix-studio-model-paths.yaml
  model-inventory.json       # inventario opcional
```

`config/runtime-paths.example.json` contiene valores portables. `scripts/configure_models.py` crea la configuración privada y las rutas de ComfyUI. El instalador lo ejecuta automáticamente; `--comfy-dir` permite indicar otra instalación. Los valores existentes se conservan, salvo el motor seleccionado explícitamente.

Los lanzadores y Matrix Studio leen esa configuración. Las variables de entorno explícitas conservan prioridad: `MATRIX_STUDIO_COMFY_DIR`, `MATRIX_STUDIO_COMFY_PYTHON`, `MATRIX_STUDIO_QWEN_CLI`, `MATRIX_STUDIO_QWEN_MODEL`, `MATRIX_STUDIO_QWEN_ENCODER`, `MATRIX_STUDIO_QWEN_VAE` y `MATRIX_STUDIO_CUDA_DIR`. Los lanzadores Qwen también admiten `MATRIX_STUDIO_QWEN_SERVER`.

Sin configuración privada, se reutilizan rutas antiguas existentes (`Data/Packages/ComfyUI`, `QwenImageLocal/engine` y `Data/Models/Qwen`) si falta el destino nuevo. No se mueven ni eliminan automáticamente instalaciones anteriores. Para migrarlas, detén los procesos, copia los archivos y cambia la configuración; conserva una copia hasta verificar el arranque.

Consulta el inventario sin cargar modelos:

```powershell
& .\Data\Engines\ComfyUI\venv\Scripts\python.exe scripts/inventory_assets.py --save
```

El inventario informa de componentes presentes, tamaños y hashes **esperados** de los manifiestos; no calcula ni valida los hashes de los archivos instalados. Usa los descargadores con verificación SHA256 para esa comprobación. Un archivo presente no garantiza que exista un adaptador o que quepa en VRAM; MiniMax H3, por ejemplo, puede almacenarse sin estar integrado. Los motores opcionales ausentes se muestran como tales, sin impedir usar ComfyUI.

El [catálogo de imágenes](IMAGE_MODELS.md) es independiente del inventario instalado. Un VAE integrado en un checkpoint no necesita descargarse por separado. No mezcles VAE o LoRAs de SD 1.5, SDXL, Qwen y Wan.

## Forge y controles de generación

El [instalador opcional de Forge Neo](FORGE.md) crea `Data/Engines/Forge`, guarda su estado en `Runtime/Forge` y comparte `Data/Models` con Studio. No descarga checkpoints. El archivo de configuración de sesión local `assets/local-session.json`, si existe, permite dirigir los accesos locales al puerto activo y está excluido de Git.

La cola conserva sus ajustes y pausa en SQLite; consulta [detener, pausar y continuar](QUEUE_CONTROLS.md).

# Automatic1111 / Forge

Studio se conecta a una API compatible en `http://127.0.0.1:7860`. Selecciona **Automatic1111 / Forge** en imágenes y actualiza los motores después de iniciar el servidor. El adaptador no instala ni inicia automáticamente ese servidor.

## Instalación opcional probada

El instalador incluido utiliza [Forge Neo](https://github.com/Haoming02/sd-webui-forge-classic), revisión `db117cb2ac33f6a11ec281ff71ffd4cd02b2f05a`, en Windows/NVIDIA. Necesita Git y [uv](https://docs.astral.sh/uv/getting-started/installation/).

```powershell
.\MatrixStudio\install_forge.ps1 -PlanOnly
.\MatrixStudio\install_forge.ps1
.\"Abrir Forge.cmd"
```

Si uv no está en PATH ni en `Data/Assets/uv`, pasa `-Uv` con la ruta de su ejecutable. El instalador fija Python 3.13.12, PyTorch 2.14.1+cu130 y torchvision 0.29.1+cu130 en un entorno independiente. El perfil `requirements-forge.compat.txt` usa Pillow 10.4 y pillow-heif 0.20 para mantener compatibilidad con Gradio 4.40. No reemplaza un checkout existente de otra revisión.

## Rutas y uso

- Motor y entorno: `Data/Engines/Forge`.
- Estado y registros: `Runtime/Forge`.
- Checkpoints: `Data/Models/StableDiffusion`.
- LoRAs: `Data/Models/Lora`.
- VAE: `Data/Models/VAE`.
- Codificadores: `Data/Models/TextEncoders`.

El lanzador comparte los pesos del proyecto y activa `--api`, sin descargarlos ni duplicarlos. La interfaz propia está en `http://127.0.0.1:7860`. Si aparece «Sin conexión», comprueba los registros `stdout.log` y `stderr.log` de `Runtime/Forge`, espera a que responda `/sdapi/v1/sd-models` y actualiza Studio.

Se verificaron CUDA, las dependencias con `pip check` y una imagen EpicRealism de 512 × 512 y 20 pasos solicitada desde Studio. Esa comprobación no implica haber probado todos los modelos o extensiones de Forge. Los controles de cola y sus límites se explican en [QUEUE_CONTROLS.md](QUEUE_CONTROLS.md).

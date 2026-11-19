# Adaptador Qwen / stable-diffusion.cpp opcional

Este directorio contiene únicamente los lanzadores PowerShell. No incluye ejecutables, DLL ni modelos. No es necesario instalar Qwen para usar ComfyUI, Wan, AnimateDiff o TRELLIS.2.

Descarga un binario compatible desde [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp/releases) y un conjunto compatible de modelo, codificador y VAE desde la [ficha del modelo](https://huggingface.co/AtomicChat/Qwen-Image-2.1-Turbo-GGUF). Revisa las licencias y opciones de la versión elegida: estos lanzadores usan las opciones Turbo del build original indicado en el [README principal](../README.md).

Coloca los ejecutables y sus dependencias CUDA en `engine/`, y los pesos en `../Data/Models/Qwen/` con los nombres `model.gguf`, `encoder.gguf` y `vae.safetensors`, o define:

```powershell
$env:MATRIX_STUDIO_QWEN_MODEL = 'D:/models/qwen/model.gguf'
$env:MATRIX_STUDIO_QWEN_ENCODER = 'D:/models/qwen/encoder.gguf'
$env:MATRIX_STUDIO_QWEN_VAE = 'D:/models/qwen/vae.safetensors'
$env:MATRIX_STUDIO_CUDA_DIR = 'D:/tools/sd-cpp-cuda'
```

Las rutas son ejemplos genéricos. No se busca ningún modelo en el Escritorio ni se reutiliza una instalación personal de otro programa. El arranque independiente del servidor Qwen usa el puerto local 1235; Matrix Studio usa `sd-cli.exe` para cada imagen. El adaptador es opcional y no se ha vuelto a validar con un binario descargado de cero en esta publicación.

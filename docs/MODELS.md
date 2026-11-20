# Descargas de modelos y LoRA

El catálogo preparatorio de checkpoints de imagen está en [`image_models.json`](../MatrixStudio/image_models.json). Consulta [su formato, versiones y alcance](IMAGE_MODELS.md). Todavía no está conectado al instalador ni al formulario de generación; sus pesos no se suman a los conjuntos instalables descritos abajo.

Los pesos no se redistribuyen en este repositorio. Cada manifiesto conserva repositorio de origen, archivo, destino y SHA256. El instalador verifica el hash completo y renombra el archivo parcial solo al terminar. Los tamaños son los de los archivos verificados en el equipo de prueba; no incluyen Python, PyTorch, cachés ni resultados. Consulta la licencia y condiciones de cada ficha antes de descargar.

## Wan 5B

Instalación: `python MatrixStudio/install_wan5b.py`. Manifiesto: [`wan5b_models.json`](../MatrixStudio/wan5b_models.json).

| Archivo | Destino bajo `Data/Models` | GB decimales | Origen |
|---|---|---:|---|
| `Wan2.2-TI2V-5B-Q5_K_M.gguf` | `DiffusionModels` | 3.81 | [QuantStack/Wan2.2-TI2V-5B-GGUF](https://huggingface.co/QuantStack/Wan2.2-TI2V-5B-GGUF) |
| `wan2.2_vae.safetensors` | `VAE` | 1.41 | [Comfy-Org/Wan_2.2_ComfyUI_Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged) |
| `umt5-xxl-encoder-Q3_K_S.gguf` | `TextEncoders` | 2.86 | [city96/umt5-xxl-encoder-gguf](https://huggingface.co/city96/umt5-xxl-encoder-gguf) |

Total de este conjunto: **8.08 GB**.

## Wan 14B

Instalación: `python MatrixStudio/install_wan.py`. Manifiesto: [`wan_models.json`](../MatrixStudio/wan_models.json).

| Archivo | Destino bajo `Data/Models` | GB decimales | Origen |
|---|---|---:|---|
| `Wan2.2-I2V-A14B-HighNoise-Q3_K_S.gguf` | `DiffusionModels` | 6.52 | [QuantStack/Wan2.2-I2V-A14B-GGUF](https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF) |
| `Wan2.2-I2V-A14B-LowNoise-Q3_K_S.gguf` | `DiffusionModels` | 6.52 | [QuantStack/Wan2.2-I2V-A14B-GGUF](https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF) |
| `umt5-xxl-encoder-Q3_K_S.gguf` | `TextEncoders` | 2.86 | [city96/umt5-xxl-encoder-gguf](https://huggingface.co/city96/umt5-xxl-encoder-gguf) |
| `wan_2.1_vae.safetensors` | `VAE` | 0.25 | [Comfy-Org/Wan_2.2_ComfyUI_Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged) |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors` | `Lora` | 1.23 | [Comfy-Org/Wan_2.2_ComfyUI_Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged) |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors` | `Lora` | 1.23 | [Comfy-Org/Wan_2.2_ComfyUI_Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged) |

Total de este conjunto: **18.60 GB**.

## AnimateDiff

Instalación: `python MatrixStudio/install_animatediff.py`. Manifiesto: [`animatediff_models.json`](../MatrixStudio/animatediff_models.json).

| Archivo | Destino bajo `Data/Models` | GB decimales | Origen |
|---|---|---:|---|
| `v1-5-pruned-emaonly-fp16.safetensors` | `StableDiffusion` | 2.13 | [Comfy-Org/stable-diffusion-v1-5-archive](https://huggingface.co/Comfy-Org/stable-diffusion-v1-5-archive) |
| `mm_sd15_v3.safetensors` | `AnimateDiff` | 0.84 | [conrevo/AnimateDiff-A1111](https://huggingface.co/conrevo/AnimateDiff-A1111) |
| `DreamShaper_8_pruned.safetensors` | `StableDiffusion` | 2.13 | [Lykon/DreamShaper](https://huggingface.co/Lykon/DreamShaper) |
| `mm_sd15_v2.safetensors` | `AnimateDiff` | 0.91 | [conrevo/AnimateDiff-A1111](https://huggingface.co/conrevo/AnimateDiff-A1111) |
| `v2_lora_ZoomOut.ckpt` | `AnimateDiffMotionLora` | 0.08 | [guoyww/animatediff](https://huggingface.co/guoyww/animatediff) |
| `v2_lora_PanLeft.ckpt` | `AnimateDiffMotionLora` | 0.08 | [guoyww/animatediff](https://huggingface.co/guoyww/animatediff) |
| `Realistic_Vision_V6.0_NV_B1_fp16.safetensors` | `StableDiffusion` | 2.13 | [SG161222/Realistic_Vision_V6.0_B1_noVAE](https://huggingface.co/SG161222/Realistic_Vision_V6.0_B1_noVAE) |
| `vae-ft-mse-840000-ema-pruned.safetensors` | `VAE` | 0.33 | [stabilityai/sd-vae-ft-mse-original](https://huggingface.co/stabilityai/sd-vae-ft-mse-original) |
| `rife_v4.26.safetensors` | `FrameInterpolation` | 0.02 | [Comfy-Org/Frame-Interpolation](https://huggingface.co/Comfy-Org/Frame-Interpolation) |

Total de este conjunto: **8.66 GB**.

## TRELLIS.2

Instalación: `python MatrixStudio/install_trellis.py`. Manifiesto: [`trellis_models.json`](../MatrixStudio/trellis_models.json).

| Archivo | Destino bajo `Data/Models` | GB decimales | Origen |
|---|---|---:|---|
| `trellis_2_int8_convrot.safetensors` | `DiffusionModels` | 5.25 | [Comfy-Org/TRELLIS.2](https://huggingface.co/Comfy-Org/TRELLIS.2) |
| `trellis_2_shape_vae_bf16.safetensors` | `VAE` | 1.10 | [Comfy-Org/TRELLIS.2](https://huggingface.co/Comfy-Org/TRELLIS.2) |
| `trellis_2_texture_vae_bf16.safetensors` | `VAE` | 0.95 | [Comfy-Org/TRELLIS.2](https://huggingface.co/Comfy-Org/TRELLIS.2) |
| `dino_v3_vit_l.safetensors` | `ClipVision` | 1.21 | [Comfy-Org/TRELLIS.2](https://huggingface.co/Comfy-Org/TRELLIS.2) |
| `birefnet.safetensors` | `BackgroundRemoval` | 0.44 | [Comfy-Org/BiRefNet](https://huggingface.co/Comfy-Org/BiRefNet) |

Total de este conjunto: **8.95 GB**.

Los cuatro conjuntos completos contienen **22 archivos distintos**, aproximadamente **41.43 GB** al deduplicar el codificador UMT5 compartido. Se recomienda espacio adicional para entornos, cachés y montajes. No necesitas todos los conjuntos: para vídeo local empieza por Wan 5B; para imágenes y AnimateDiff usa su conjunto.

## Qwen opcional

Los lanzadores de Qwen no tienen descarga automática porque deben emparejarse un ejecutable compatible, su runtime CUDA y tres pesos del mismo conjunto. Consulta [QwenImageLocal](../QwenImageLocal/README.md). No se requiere LM Studio ni se incluyen sus bibliotecas. Automatic1111/Forge utiliza sus propios checkpoints y se configura por API local.

Motores y pesos: [organización, compatibilidad e inventario](LOCAL_ASSETS.md). Vídeo: [parámetros de las pruebas de sparring](VIDEO_TUNING.md).

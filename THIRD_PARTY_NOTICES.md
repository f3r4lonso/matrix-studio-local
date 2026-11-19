# Componentes de terceros

La licencia MIT de este repositorio cubre el código original de Matrix Studio y sus lanzadores. No sustituye las licencias de modelos, motores ni bibliotecas.

| Componente | Distribución en este repositorio | Licencia / fuente |
|---|---|---|
| Google model-viewer 4.4.0 | JavaScript del visor y avisos de licencia | [Apache-2.0](MatrixStudio/assets/model-viewer.LICENSE), [fuente](https://github.com/google/model-viewer/tree/v4.4.0) |
| Dependencias integradas en model-viewer | Se conservan los comentarios de licencia del bundle | [Avisos integrados](docs/model-viewer-bundled-notices.txt) y licencias de [three.js](MatrixStudio/assets/three.LICENSE) y [Lit](MatrixStudio/assets/lit.LICENSE) |
| ComfyUI | No se redistribuye; el instalador descarga un commit fijado | [GPL-3.0](https://github.com/Comfy-Org/ComfyUI/blob/master/LICENSE) |
| ComfyUI-GGUF | Se descarga por separado | [Apache-2.0](https://github.com/city96/ComfyUI-GGUF) |
| AnimateDiff Evolved | Se descarga por separado | [Apache-2.0](https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved) |
| PyTorch, aiohttp, Pillow, PyAV y demás paquetes | Se instalan desde sus distribuidores | Cada paquete conserva su licencia |
| Pesos de imágenes, vídeo, 3D y LoRA | No incluidos; enlaces y hashes en manifiestos | Consultar cada ficha enlazada en [MODELS.md](docs/MODELS.md) |
| Imagen de panda | Recurso ilustrativo generado con IA; sin metadatos de generación | No representa a una persona ni contiene datos de una sesión privada |

Matrix Studio utiliza las APIs de motores independientes. No es una distribución oficial de Stability Matrix, ComfyUI, Microsoft TRELLIS.2, Wan ni Hugging Face. Los nombres se usan para describir compatibilidad.

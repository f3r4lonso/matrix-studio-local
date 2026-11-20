# Catálogo de modelos de imagen

[`MatrixStudio/image_models.json`](../MatrixStudio/image_models.json) fija ocho checkpoints y una referencia de VAE externo. Es un catálogo preparatorio: el servidor, los instaladores y la interfaz todavía no lo consumen. No descarga archivos ni cambia los ajustes de generación actuales.

| Clave | Versión | Arquitectura | VAE |
|---|---|---|---|
| `pony_v6_xl` | V6, versión Civitai 290640 | SDXL / Pony | Incorporado |
| `juggernaut_xl_v9` | V9 + RunDiffusionPhoto 2 | SDXL | Incorporado |
| `dreamshaper_xl_alpha2` | Alpha2, SDXL 1.0 | SDXL | Incorporado, fixed VAE |
| `dreamshaper_xl_lightning` | Lightning DPM++ SDE | SDXL Lightning | Incorporado |
| `epicrealism_natural_sin_rc1_vae` | Natural Sin RC1 VAE | SD 1.5 | Incorporado |
| `ghostmix_v2_baked_vae` | v2.0-BakedVAE | SD 1.5 | Incorporado |
| `ghostxl_v1_baked_vae` | v1.0-Baked VAE | SDXL | Incorporado |
| `rev_animated_v2_rebirth_vae` | V2 Rebirth+VAE | SD 1.5 | Incorporado |

## Contrato del archivo, versión 1

- `schema_version` identifica el formato del catálogo; no es la versión de un modelo.
- `models` contiene checkpoints completos para texto a imagen; `vaes` contiene archivos de VAE independientes.
- `key` es una identidad estable, independiente del nombre del archivo. `version` conserva la denominación del distribuidor.
- `architecture` usa `sd15` o `sdxl` para el workflow. `base_model` conserva la etiqueta original, incluida la aceleración Lightning. `lora_family` distingue `sd15`, `sdxl` y `pony`; es una guía de selección, no una garantía de compatibilidad de cualquier LoRA.
- `source` identifica proveedor, ficha, API de metadatos y URL de descarga. Civitai fija `model_id`, `version_id` y `file_id`. Hugging Face fija repositorio y commit. `mirrors`, si existe, identifica la misma secuencia de bytes con otro distribuidor; el nombre remoto puede ser distinto.
- `file` es el nombre de destino bajo `Data/Models/<folder>`. `sha256` es el hash completo de esos bytes en minúsculas. `size_bytes` es el tamaño publicado por el proveedor.
- `vae.mode: checkpoint` utiliza el VAE del checkpoint; `external_key: null` indica que no requiere una descarga adicional. Una futura entrada con `mode: external` deberá referenciar una clave de `vaes` compatible con su arquitectura.
- `recommended` describe la primera pasada: dimensiones, pasos, CFG, sampler, scheduler, CLIP skip y textos iniciales. Los nombres de sampler y scheduler son los de ComfyUI; el adaptador A1111 deberá traducirlos.
- `clip_skip: null` conserva el comportamiento nativo del motor. Los enteros usan la convención positiva A1111. En ComfyUI no se debe restar ese valor al comportamiento por defecto: SDXL ya usa la penúltima capa, equivalente al ajuste requerido por Pony.
- `recommendation_sources` enlaza las instrucciones consultadas. `project_default_fields` enumera los campos elegidos por el proyecto cuando el autor no fija un valor exacto. Los perfiles son editables y no garantizan calidad ni consumo de memoria.
- `verification` diferencia consulta de metadatos, comprobación local del peso y prueba real de generación. Los hashes de los nuevos checkpoints están contrastados con el proveedor; no se han descargado ni ejecutado estos pesos.

## Alcance y mantenimiento

Todos los checkpoints seleccionados incluyen VAE. La referencia `sd15_mse_840000` reutiliza el archivo y SHA256 de `animatediff_models.json`; no se aplica automáticamente ni debe usarse como VAE SDXL. No se añade un archivo llamado `epicrealism-vae` sin identificar antes su versión y hash.

GhostMix y GhostXL son entradas distintas. DreamShaper Alpha2 y Lightning tienen perfiles distintos; no se deben intercambiar sus pasos, CFG o sampler. No hay modelos SD 2.1 en esta selección.

Antes de añadir una versión, consultar sus metadatos oficiales, comprobar archivo, tamaño y SHA256, registrar su origen y distinguir recomendaciones del autor de valores propuestos. Al descargar, un futuro instalador deberá verificar el SHA256 de los bytes antes de aceptar el archivo. Civitai puede exigir autenticación o aceptación de condiciones; no almacenar tokens en este catálogo. Las licencias y condiciones son las de la versión enlazada, no la licencia MIT del código del proyecto.

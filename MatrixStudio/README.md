# Matrix Studio: código de la aplicación

La instalación, arquitectura, hardware validado, modelos y límites están documentados en el [README principal](../README.md).

No se incluyen conversaciones, imágenes, vídeos, modelos, configuraciones privadas ni registros. Los datos de una instalación nueva se crean localmente al ejecutar la aplicación.


Para instalar únicamente Pony V6 XL, Juggernaut XL v9 y EpicRealism desde el catálogo: `python MatrixStudio/install_image_models.py pony_v6_xl juggernaut_xl_v9 epicrealism_natural_sin_rc1_vae`. Los mirrors de Hugging Face están fijados a revisiones y sus hashes coinciden con el catálogo; el instalador verifica tamaño y SHA256 antes de publicar cada archivo final en la biblioteca local.

## Controles y galería

**Detener actual**, **Pausar cola** y **Continuar** controlan las generaciones pendientes. Continuar reinicia el elemento interrumpido con sus ajustes guardados; conserva las escenas completas de un montaje. La galería indica motor y modelo. Consulta [controles de cola](../docs/QUEUE_CONTROLS.md) y [Forge opcional](../docs/FORGE.md).

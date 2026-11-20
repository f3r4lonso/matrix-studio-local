# Matrix Studio Local

**Español** · Interfaz local con conversaciones y galería para crear imágenes, vídeos y objetos 3D con ComfyUI, Wan 2.2, AnimateDiff y TRELLIS.2. Este Space presenta el proyecto y enlaza la instalación local; los modelos se ejecutan en tu propio equipo.

**English** · A local chat and gallery interface for images, video and 3D with ComfyUI, Wan 2.2, AnimateDiff and TRELLIS.2. This Space introduces the project and links to local setup instructions; models run on your own computer.

- [Código / Source](https://github.com/f3r4lonso/matrix-studio-local)
- [Instalación en español](https://github.com/f3r4lonso/matrix-studio-local/blob/main/README.md)
- [English installation guide](https://github.com/f3r4lonso/matrix-studio-local/blob/main/README.en.md)

Reference hardware: RTX 5060 Laptop (8 GB VRAM), Intel i7-14650HX, 16 GB RAM, Windows 11. This documents a tested configuration, not a guarantee for every model or setting. AI montages of 6 and 10 seconds were tested; 120-second assembly was verified with synthetic scenes, not a full two-minute AI render. Anatomy and body-contact errors remain possible.

No model weights, private conversations, reference images, or generated outputs are included. Original code is MIT; external components and models retain their own licenses. The screenshot shows an empty session.

## Actualización / Update — 2026-11-20

**Español.** Motores centralizados en `Data/Engines`, modelos separados por tipo en `Data/Models` (checkpoints, codificadores, VAE y LoRAs), rutas configurables e inventario local. Se conserva compatibilidad con instalaciones anteriores. El catálogo incluye ocho checkpoints con versión, arquitectura, origen, archivo, SHA256, VAE y ajustes recomendados; catalogado no significa instalado ni probado.

**English.** Engines now share `Data/Engines`, with model assets organized under `Data/Models` (checkpoints, encoders, VAEs and LoRAs), configurable paths and a local inventory. Previous installation paths remain supported. The catalog documents eight checkpoints with versions, architectures, sources, files, SHA256, VAE information and suggested settings; catalog entries are not all installed or tested.

- [Organización e inventario / Asset organization](https://github.com/f3r4lonso/matrix-studio-local/blob/main/docs/LOCAL_ASSETS.md)
- [Catálogo de imágenes / Image model catalog](https://github.com/f3r4lonso/matrix-studio-local/blob/main/docs/IMAGE_MODELS.md)
- [Catálogo JSON / Machine-readable catalog](https://github.com/f3r4lonso/matrix-studio-local/blob/main/MatrixStudio/image_models.json)
- [Pruebas de vídeo / Video settings and limitations](https://github.com/f3r4lonso/matrix-studio-local/blob/main/docs/VIDEO_TUNING.md)

Se compararon clips de sparring de unos cinco segundos: 14B con LightX2V, cuatro pasos, CFG 1, shift 5 y Euler/simple, frente a 5B con 30 pasos, CFG 5, shift 8 y UniPC/simple. El prompt simplificado mejoró la actividad del 14B para esa referencia y semilla, pero persisten estelas y un número de golpes inexacto. Se inspeccionaron fotogramas muestreados; no se garantiza coreografía fiable.

Five-second sparring trials compared 14B/LightX2V (four steps, CFG 1, shift 5, Euler/simple) with 5B (30 steps, CFG 5, shift 8, UniPC/simple). A shorter prompt improved activity in the tested 14B scene and seed, while motion trails and imperfect action counts remain. Sampled frames were inspected; reliable choreography is not established.

Los pesos y resultados privados permanecen locales. / Model weights and private outputs remain local.

## Controles, galería y Forge / Controls, gallery and Forge

**Español.** La barra de generación permite detener el trabajo activo, pausar la cola y continuar. El elemento interrumpido vuelve a empezar con los mismos parámetros y semilla; los montajes conservan las escenas completas. La pausa persiste al reiniciar. La galería muestra el motor y el modelo de cada resultado. Forge dispone de instalación opcional con los pesos compartidos del proyecto. Se probaron localmente Pony V6 XL, Juggernaut XL v9 y EpicRealism; los pesos se descargan por separado. Pasaron 43 pruebas aisladas y una prueba real de detener y continuar en ComfyUI.

**English.** Generation controls stop the active job, pause the queue and continue pending work. An interrupted item restarts with its saved settings and seed; completed montage scenes are retained. Pause state survives restarts. Gallery cards identify the recorded engine and model. An optional Forge installer shares project weights. Pony V6 XL, Juggernaut XL v9 and EpicRealism were tested locally; weights are downloaded separately. Validation includes 43 isolated tests and a live ComfyUI stop/resume trial.

- [Controles y límites / Queue behavior and limits](https://github.com/f3r4lonso/matrix-studio-local/blob/main/docs/QUEUE_CONTROLS.md)
- [Instalar Forge / Optional Forge setup](https://github.com/f3r4lonso/matrix-studio-local/blob/main/docs/FORGE.md)

Este Space sigue siendo una presentación estática; la generación y sus controles funcionan en la instalación local. / This remains a static presentation; generation and queue controls run locally.

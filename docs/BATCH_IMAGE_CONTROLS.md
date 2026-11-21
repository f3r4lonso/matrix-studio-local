# Ajustes propios para lotes de imágenes

**Lotes JSON** tiene un panel independiente para seleccionar motor, checkpoint, VAE, LoRAs, ancho, alto, pasos, CFG, semilla base, negativo general, sampler y scheduler. Los componentes se consultan en el motor conectado mediante **Actualizar componentes**; no se descargan pesos.

Una LoRA se añade con **Añadir LoRA**. ComfyUI permite intensidades independientes para modelo y CLIP; Automatic1111 / Forge utiliza una intensidad común. Se admiten hasta ocho LoRAs, con intensidades entre −2 y 2. Las palabras de activación requeridas por cada adaptador deben incluirse en los prompts.

La arquitectura se identifica a partir del nombre y de metadatos locales disponibles. Se impide aplicar un adaptador de vídeo, de otra familia o de arquitectura desconocida a un checkpoint SD 1.5 o SDXL. La coincidencia de familia es un filtro preventivo, no una certificación de calidad para todas las variantes. Los VAE externos también requieren coincidencia; **VAE del modelo / automático** conserva la opción incorporada en el checkpoint.

## Capacidades de cada motor

| Función | ComfyUI | Automatic1111 / Forge | Qwen CLI actual |
|---|---|---|---|
| Modelo | Checkpoints expuestos por el motor | Checkpoints expuestos por el motor | Qwen configurado |
| VAE externo | Sí | Sí; Forge Neo usa módulos adicionales | VAE fijo |
| LoRAs | Cadena de LoraLoader | Etiquetas LoRA en el prompt enviado | No expuestas por este flujo |
| Sampler / scheduler | Opciones del KSampler instalado | Opciones de la API instalada | Euler y configuración fija |
| Imagen inicial | LoadImage → VAEEncode | API img2img | No expuesta por este flujo |

Los controles no admitidos por el adaptador quedan desactivados. Esto describe el flujo de Studio, no todas las capacidades que puede ofrecer un motor en otra interfaz.

## Imagen a imagen

En **Imagen inicial · imagen a imagen**, sube un PNG, JPG o WebP de hasta 20 MB. Se conserva una referencia local, se corrige su orientación y se utiliza para todas las entradas del lote. La imagen se ajusta mediante recorte central a las dimensiones elegidas. La transformación (`denoise`) controla cuánto puede cambiar: un valor bajo mantiene más la referencia. **Quitar imagen inicial** devuelve el lote a texto a imagen.

Este control no es un editor de máscaras ni un flujo de inpainting. Utiliza los mismos modelos, VAE y LoRAs elegidos en el panel.

## Prioridad de ajustes y recuperación

Por defecto se usan los controles del panel. **Priorizar settings del JSON** permite que los campos incluidos en el archivo tengan prioridad; los omitidos conservan los valores del panel. El negativo propio de cada entrada siempre tiene prioridad sobre el negativo general.

Cada trabajo guarda los parámetros efectivos, LoRAs, intensidades y referencia. Al retomar se reutilizan esas opciones y la semilla, y la descripción de la imagen muestra los parámetros guardados.

**Editar ajustes pendientes** carga las opciones de la primera entrada pendiente. Pausa la cola y deja terminar o detén el trabajo activo antes de **Aplicar a pendientes**. Se actualizan únicamente entradas en cola, pausadas o con error; las imágenes terminadas conservan sus parámetros y archivos. Se mantienen las semillas y los negativos existentes de cada entrada. Aplicar ajustes no reanuda automáticamente: pulsa **Retomar pendientes** cuando corresponda.

## API

- `GET /api/image-options?engine=comfy` devuelve componentes y arquitecturas detectadas. `engine` también acepta `automatic` y `qwen`; `refresh=1` renueva la información almacenada temporalmente.
- `POST /api/image/input` acepta multipart con un campo `image` y devuelve `name` y `url` para la referencia local.
- `POST /api/image-batches` acepta las opciones anteriores dentro de `settings`; `prefer_ui_settings: true` prioriza los ajustes exteriores sobre los del documento.
- `POST /api/image-batches/{id}/settings` cambia las opciones de los trabajos pendientes mientras la cola está pausada y sin un trabajo activo.

Ejemplo de opciones comunes:

```json
{
  "engine": "comfy",
  "model": "checkpoint.safetensors",
  "vae": "",
  "loras": [{"name": "adapter.safetensors", "strength_model": 0.8, "strength_clip": 0.8}],
  "width": 1024,
  "height": 1024,
  "steps": 25,
  "cfg": 6,
  "sampler": "euler",
  "scheduler": "normal",
  "seed": -1,
  "negative": "blurry",
  "input_image": "",
  "denoise": 0.65
}
```

Los nombres del ejemplo son ilustrativos; selecciona componentes instalados compatibles. La revisión está pendiente de pruebas funcionales, visuales y de GPU; no se ejecutaron pruebas para esta modificación.

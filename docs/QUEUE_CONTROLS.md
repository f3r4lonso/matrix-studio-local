# Frenar, pausar y continuar

Los controles de la barra superior afectan a la cola de esta instancia de Matrix Studio:

| Control | Comportamiento |
|---|---|
| Pausar cola | Deja terminar el trabajo activo y retiene los siguientes. También admite nuevos trabajos mientras está pausada. |
| Detener actual | Pausa la cola e intenta interrumpir el trabajo activo. Espera la respuesta del motor antes de permitir continuar. |
| Continuar | Devuelve los trabajos detenidos a la cola y permite ejecutar los pendientes, conservando su orden. |

Continuar conserva el prompt, modelo, ajustes y semilla. La imagen o escena interrumpida **empieza de nuevo**; no se recupera el paso exacto de difusión. En montajes se conservan las escenas ya terminadas y se reintenta la escena pendiente. Las operaciones de escritura y ensamblado esperan un punto seguro antes de liberar el trabajo.

La pausa se guarda en SQLite. Tras reiniciar Studio, un trabajo que figuraba en ejecución queda pausado para evitar repetirlo automáticamente. Solo debe ejecutarse una instancia de Studio sobre una misma base de datos; la coordinación de colas no abarca varias instancias.

## Motores

- ComfyUI: elimina únicamente las solicitudes pendientes propias e interrumpe el identificador de prompt propio. Requiere una versión con interrupción dirigida por `prompt_id`; no vacía la cola de otros clientes.
- Automatic1111 / Forge: identifica la tarea mediante `force_task_id` y consulta `/internal/progress` antes de solicitar la interrupción. La API de interrupción del motor es global; usar una instancia dedicada evita carreras con otros clientes. Si no puede identificar la tarea, Studio informa del error y mantiene pausada su cola sin interrumpir a ciegas.
- Qwen: detiene el proceso CLI creado para ese trabajo. No termina procesos externos.

La latencia depende del motor y del punto de cálculo. Si falla la interrupción, el trabajo activo puede seguir hasta terminar; el mensaje de error permanece visible y los pendientes siguen retenidos.

## API

`GET /api/queue/status` devuelve `paused`, `stopping`, `active_id`, `queued`, `paused_jobs` y `error`.

`POST /api/queue/pause`, `POST /api/queue/stop` y `POST /api/queue/resume` aceptan `{}`. Reanudar durante una interrupción devuelve un error hasta que se confirme su finalización.

## Comprobaciones

La suite pública incluye diez pruebas de cola: pausa y orden, reanudación sin duplicados, espera de confirmación, errores de interrupción, recuperación tras reinicio, solicitudes ComfyUI propias, identificación de tareas Forge, recuperación de escenas y limpieza del proceso Qwen.

La prueba local con ComfyUI detuvo un prompt en ejecución, conservó el siguiente trabajo y completó ambos al continuar con sus semillas originales. Otra prueba retiró una solicitud propia pendiente sin interrumpir un vídeo de otro cliente. Los datos y resultados de esas pruebas permanecen locales.

## Galería

Cada resultado muestra el motor registrado y el nombre del modelo. Qwen se identifica como `Qwen · stable-diffusion.cpp`; el adaptador HTTP figura como `Automatic1111 / Forge`, porque los registros históricos no distinguen ambos servidores. Los resultados antiguos sin esos metadatos muestran `Motor no registrado` o `Modelo no registrado`.

## Lotes JSON

Los [lotes de imágenes](JSON_BATCHES.md) usan estos mismos controles. Un error en un elemento pausa la cola y Continuar lo reintenta antes de los posteriores. Se mantienen los resultados terminados y el orden del archivo.

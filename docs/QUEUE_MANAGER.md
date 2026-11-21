# Cola visual de imágenes, vídeos y 3D

**Cola de trabajos** muestra el trabajo activo por separado y agrupa los pendientes por lote o conversación. Las listas aparecen plegadas, con título y miniaturas. **Desplegar listas** y **Plegar listas** permiten cambiar la vista conjunta. Los lotes de la sección JSON también son desplegables.

Las miniaturas muestran referencias existentes. Un trabajo de texto a imagen todavía no tiene una imagen final: se representa con un marcador hasta generarse. Los resultados terminados siguen en la galería y sus álbumes.

## Selección y cancelación

- Cada pendiente se puede seleccionar o cancelar individualmente.
- **Seleccionar pendientes**, dentro de un grupo, permite actuar sobre esa lista.
- **Cancelar pendientes del grupo** conserva el trabajo activo.
- **Cancelar activo** solicita una interrupción usando el adaptador del motor. Espera su confirmación y después continúa con los siguientes si la cola estaba en marcha. Una pausa solicitada durante la interrupción se respeta.
- Los cancelados permanecen guardados con el estado `cancelled`. **Continuar** no los reactiva. Activa **Incluir cancelados** y utiliza **Volver a encolar** para recuperarlos explícitamente.

La cancelación es inmediata para los pendientes y no pide confirmación. No borra las imágenes o vídeos terminados ni los archivos de recuperación. Un error al detener el motor deja un aviso y conserva la pausa de la cola.

## Prioridad

Selecciona trabajos y aplica prioridad alta, normal o baja. **Primero**, **Subir** y **Bajar** permiten ajustar un trabajo pendiente. La posición indicada corresponde al orden entre trabajos realmente encolados; los pausados y los que tienen error necesitan reencolarse o retomarse.

La prioridad y el orden se guardan en SQLite. El siguiente trabajo se elige desde la base de datos para que un cambio de prioridad se aplique aunque existan señales antiguas en la cola de memoria. El activo no cambia de posición ni admite edición.

Cambiar el orden rompe deliberadamente el orden original del JSON para los trabajos afectados. Sin cambios manuales de prioridad se mantiene el orden de importación. Nunca se vuelve a ejecutar automáticamente una imagen terminada.

## Edición de pendientes

Al pulsar **Editar**, Studio pausa el inicio de los siguientes trabajos; el actual puede terminar. La edición se rechaza si el trabajo seleccionado ya está activo.

- Imágenes: se abre el panel de controles con motor, modelo, VAE, LoRAs, prompt, negativo, tamaño, pasos, CFG, semilla, sampler y referencia. **Guardar trabajo pendiente** cambia únicamente ese trabajo.
- Vídeos: un diálogo permite cambiar título, prompt, negativo, dimensiones, pasos, CFG, semilla, fotogramas, interpolación y duración o guion de montaje. Se conserva la familia del modelo; los FPS de Wan siguen siendo los nativos. AnimateDiff admite sus FPS y transformación dentro de los límites del adaptador.
- 3D: se pueden cambiar título, nombre descriptivo, pasos, caras objetivo y semilla.

Guardar no reanuda automáticamente una cola pausada. Si el trabajo estaba cancelado, guardar tampoco lo reactiva: utiliza **Volver a encolar**. Si estaba con error, utiliza **Reintentar** o el control de continuación apropiado.

Si se cambian el prompt o los parámetros de un montaje que ya tenía escenas guardadas, su carpeta se archiva dentro de `video_projects` con el sufijo `-before-edit-<id>`. Las escenas originales se conservan y el montaje editado se recalcula, evitando combinar escenas de configuraciones diferentes.

## Nombres de álbum

Los archivos nuevos envían `source_filename`; el álbum y su conversación toman el nombre del archivo, incluida su extensión `.json`. El nombre del archivo no altera la huella del contenido y ajustes usada para evitar importaciones duplicadas. Reimportar una coincidencia conserva los trabajos y actualiza el nombre del álbum.

Las versiones anteriores no guardaban el nombre del archivo. Esos álbumes incluyen **Cambiar nombre** para asignarlo sin reimportar ni generar de nuevo.

## API

- `GET /api/queue/jobs`: trabajos, grupos, tipo, parámetros, referencia, estado y prioridad.
- `POST /api/queue/cancel`: `{"ids":["<id>"],"pending_only":true}`. Con `pending_only: false`, o sin ese campo, puede cancelar el activo seleccionado.
- `POST /api/queue/priority`: `{"ids":["<id>"],"priority":10}` o `{"ids":["<id>"],"move":"first"}`. Los movimientos admitidos son `first`, `up`, `down` y `last`.
- `POST /api/queue/requeue`: `{"ids":["<id>"]}`. Conserva ajustes, semilla y prioridad; respeta la pausa global.
- `POST /api/queue/jobs/{id}/edit`: `{"title":"Nombre","prompt":"Descripción","params":{...}}`. Los campos permitidos dependen del tipo de trabajo.
- `POST /api/image-batches/{id}/name`: `{"name":"coleccion.json"}`.

Se incorporan `queue_priority`, `queue_order`, `cancel_requested` y `queue_title` a los resultados, y `source_filename` a los lotes. La migración conserva los registros existentes. Usa una sola instancia activa de Studio para cada base de datos.

Esta revisión queda pendiente de pruebas funcionales, visuales y de GPU. No se ejecutaron pruebas ni se generaron trabajos de prueba para esta modificación.

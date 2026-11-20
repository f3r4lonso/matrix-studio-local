# Lotes de imágenes desde JSON

En **Crear imágenes**, selecciona motor, modelo y ajustes. Abre **Lotes JSON**, carga el archivo y pulsa **Guardar lote en la cola**. La vista previa indica el orden; el panel de progreso conserva el estado de cada imagen. **Ver imágenes del lote** abre su conversación.

## Formato

Se acepta un objeto para una imagen o una lista para varias:

```json
[
  {
    "numero": 25,
    "numero_pokedex": "#025",
    "nombre": "Pikachu",
    "prompt": "A small yellow wild rodent in a forest, realistic wildlife photography",
    "negative_prompt": "cartoon, anime, cgi, plastic, toy"
  },
  {
    "numero": 26,
    "numero_pokedex": "#026",
    "nombre": "Raichu",
    "prompt": "An orange brown wild rodent in a forest, realistic wildlife photography",
    "negative_prompt": "cartoon, anime, cgi, plastic, toy"
  }
]
```

`nombre` y `name` son equivalentes. `numero` y `numero_pokedex` son opcionales y se conservan como metadatos; no reordenan la lista. Cada entrada genera exactamente una imagen, incluso si dos prompts son iguales. El negativo de cada entrada tiene prioridad sobre el negativo general; una cadena vacía lo elimina para esa imagen.

También se admite `{ "name": "Mi colección", "prompts": [...] }`, con objetos como los anteriores o cadenas de texto. Un campo `settings` opcional en ese objeto puede definir `engine`, `model`, `width`, `height`, `steps`, `cfg`, `seed` y `negative`; los campos omitidos toman los ajustes de la interfaz. La importación desde la interfaz permite hasta 1000 entradas y archivos de hasta 2 MB. Usa JSON UTF-8 válido, sin comentarios ni comas finales. El ejemplo descargable desde la app proporciona la estructura completa.

## Orden y recuperación

- Se valida el lote completo antes de guardarlo: un elemento inválido no deja un lote importado a medias.
- Se guardan todas las entradas y sus semillas en una transacción SQLite antes de empezar a generar.
- Se utiliza la cola secuencial: otros trabajos ya encolados pueden ejecutarse antes del lote.
- **Pausar cola** deja terminar la imagen activa y retiene las siguientes.
- **Detener actual** pausa la cola e interrumpe el trabajo propio; **Continuar** reintenta esa imagen con sus parámetros y semilla. No recupera el paso exacto de difusión.
- Si una imagen del lote falla, se pausa la cola. Corrige la causa y pulsa **Continuar**: esa imagen se reintenta antes que las siguientes. Las terminadas no se repiten.
- El progreso persiste tras cerrar el navegador o reiniciar Studio. Una generación interrumpida al reiniciar requiere continuar explícitamente.
- Importar el mismo contenido normalizado y ajustes devuelve el lote existente. Cambiar los ajustes o el contenido crea otro lote. Para recuperar un lote, utiliza su progreso guardado y los controles; no necesitas volver a importar.

Los controles afectan a toda la cola de la instancia. Ejecuta una sola instancia por base de datos. Los límites de interrupción por motor están documentados en [QUEUE_CONTROLS.md](QUEUE_CONTROLS.md).

La galería muestra el nombre y la posición del elemento, además de motor y modelo. Las descargas llevan un prefijo de posición y un nombre saneado; las rutas internas siguen usando identificadores únicos. Borrar voluntariamente una imagen no hace que el lote la genere de nuevo; puede recuperarse con Deshacer.

## API

`POST /api/image-batches` acepta el objeto/lista anterior. Para enviar ajustes comunes junto a una lista o un objeto individual:

```json
{
  "document": [{"nombre": "Ejemplo", "prompt": "A forest", "negative_prompt": "blurry"}],
  "settings": {"engine": "comfy", "model": "checkpoint.safetensors", "seed": 42}
}
```

La respuesta contiene `id`, `chat`, `count` y `existing`. `GET /api/image-batches` devuelve lotes, progreso y elementos en orden. Para pausar, detener o continuar se usan las rutas de cola existentes.

Ocho pruebas aisladas cubren validación atómica, orden y nombres, deduplicación, pausa ante errores, interrupción/reintento, progreso tras reinicio, prompts repetidos, semillas guardadas y los campos del formato Pokémon. Los adaptadores GPU se sustituyen en estas pruebas; no equivalen a ocho renders reales.

## API

`POST /api/image-batches` acepta `{ "document": <objeto o lista del archivo>, "settings": { "engine": "comfy", "model": "checkpoint.safetensors" } }`. También acepta directamente un objeto de lote con `prompts` y `settings`. Devuelve `id`, `chat`, `count` y `existing`. `GET /api/image-batches` devuelve el progreso y las entradas ordenadas. Importar de nuevo recupera el registro existente; no reanuda automáticamente una cola pausada.

La deduplicación compara contenido normalizado, nombres, metadatos y ajustes. Cambiar cualquiera de ellos crea otro lote. Las semillas aleatorias se eligen una vez al guardar y se reutilizan al reintentar. El nombre visible y el índice se incluyen al descargar desde Studio; los archivos internos conservan identificadores seguros.

Ocho pruebas específicas cubren validación atómica, orden, negativos y metadatos del formato Pokémon, prompts repetidos, importación sin duplicados, errores, detención y recuperación tras reinicio. La suite pública completa tiene 51 pruebas. Esta versión requiere reiniciar el servidor local para registrar las nuevas rutas API; actualizar solo la pestaña no recarga Python.

## Si aparece un error al importar

Un HTTP 404 en `/api/image-batches` significa que la pestaña ha cargado los archivos nuevos, pero el proceso Python abierto pertenece a la versión anterior. Reinicia el servidor para registrar la API nueva. Recargar la pestaña o volver a abrir un lanzador que detecta el mismo servidor existente no recarga el backend. La interfaz distingue ahora este caso y muestra una instrucción específica en lugar del error genérico de petición.

Cada lote incluye **Retomar pendientes**. Reintenta el primer error antes de seguir y conserva los resultados terminados. La reanudación también reconstruye las entradas pendientes de la cola desde SQLite. Los controles de cola funcionan aunque una pestaña antigua no incluya los controles GPU nuevos.

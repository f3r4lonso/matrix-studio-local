# Colecciones de imágenes desde JSON

En **Lotes JSON**, descarga **coleccion-ejemplo.json**, selecciona motor y ajustes, carga tu archivo y pulsa **Guardar lote en la cola**. El álbum utiliza el nombre del archivo. Se genera una imagen por entrada y se conserva el orden del documento salvo cambios explícitos de prioridad.

## Formato genérico

```json
[
  {
    "ID": 1,
    "Titulo": "Bosque al amanecer",
    "Descripcion": "Un paisaje tranquilo.",
    "Prompt": "A peaceful forest at sunrise, golden light, detailed landscape photography",
    "PromptNegativo": "text, watermark, blurry",
    "Categoria": "Paisaje",
    "Iluminacion": "Luz cálida"
  },
  {
    "ID": 2,
    "Titulo": "Ciudad junto al río",
    "Descripcion": "Edificios reflejados en el agua.",
    "Prompt": "A modern riverside city at blue hour, realistic architectural photography"
  }
]
```

Cada entrada del formato nuevo requiere **ID, Titulo, Descripcion y Prompt**. **PromptNegativo** es opcional.

- **ID** es el identificador visible de la imagen en la colección: entero o texto no vacío, de hasta 80 caracteres. No cambia el orden de la cola ni sustituye al identificador interno del trabajo.
- **Titulo** contiene entre 1 y 120 caracteres.
- **Descripcion** es texto y puede ser una cadena vacía.
- **Prompt** contiene entre 1 y 12000 caracteres y es el texto enviado al modelo.
- **PromptNegativo**, si se proporciona, admite hasta 12000 caracteres. Omitirlo o usar null permite el negativo general del lote. Una cadena vacía elimina el negativo para esa imagen.

Se aceptan mayúsculas, acentos y variantes habituales como Título, Descripción, prompt, promt, prompt_negativo, negative_prompt y Promt negativo. Los alias ambiguos con valores diferentes se rechazan antes de guardar el lote.

## Cómo se forma la descripción

La descripción visible es:

**Descripcion + propiedad adicional 1 + propiedad adicional 2 + …**

Se escribe primero el texto de Descripcion y después cada propiedad adicional como **Nombre: valor**, en el orden en que aparece en la entrada JSON. Los bloques se separan por una línea en blanco.

El primer ejemplo produce:

```text
Un paisaje tranquilo.

Categoria: Paisaje

Iluminacion: Luz cálida
```

Las listas y los objetos anidados se conservan como JSON legible; también se representan números, booleanos y null. La descripción compuesta puede tener hasta 100000 caracteres.

**Las propiedades adicionales no se añaden al prompt ni cambian los ajustes del motor.** Por ejemplo, una propiedad Material o Categoria describe la ficha; no modifica la generación. Los parámetros técnicos se eligen en el [panel del lote](BATCH_IMAGE_CONTROLS.md), o en settings del envoltorio de colección cuando se usa esa opción.

Si ya existe un Titulo explícito, una propiedad adicional nombre o name se incorpora a la descripción; de igual manera, numero se conserva como propiedad adicional cuando ya existe ID. Así no se pierden datos por coincidir con alias de formatos antiguos.

## Formas de documento y compatibilidad

El archivo puede ser una lista, un único objeto de imagen, o un envoltorio `{ "name": "Colección", "prompts": [...] }`. El envoltorio admite settings; esas opciones pertenecen a la colección, no son propiedades de una imagen. Dentro de una imagen, cualquier propiedad ajena a sus campos principales se incorpora a la descripción, incluida una propiedad settings.

Los formatos anteriores con nombre/name, numero, prompt y negative_prompt se mantienen compatibles y se normalizan al formato genérico. Si faltaban ID o descripción se utiliza la posición como ID y una descripción base vacía. Los metadatos antiguos conservados se añaden a la descripción. Las propiedades que una versión anterior descartó solo pueden recuperarse desde el archivo original.

Al reimportar una coincidencia de contenido generativo y ajustes se actualizan los metadatos de descripción sin duplicar las imágenes ni repetir las terminadas. La compatibilidad con las huellas anteriores permite enriquecer registros de formatos antiguos cuando coinciden sus datos y ajustes originales.

## Guardado y recuperación

El archivo de la interfaz admite hasta 1000 entradas y 2 MB. Usa JSON UTF-8 válido. Se valida el documento completo antes de guardar sus trabajos en una transacción SQLite. Las semillas aleatorias se eligen una sola vez y se conservan para reintentar.

**Pausar cola** deja terminar el trabajo activo. **Detener actual** interrumpe el trabajo propio y pausa los siguientes. **Retomar pendientes** reintenta los errores y continúa sin repetir resultados terminados. Los cancelados solo se recuperan mediante **Volver a encolar** en [Cola de trabajos](QUEUE_MANAGER.md). Un elemento interrumpido vuelve a empezar con sus ajustes; no se recupera el paso exacto de difusión.

El progreso permanece guardado al cerrar el navegador o reiniciar Studio. Los controles afectan a la cola de la instancia. El nombre del archivo no altera la protección contra importaciones duplicadas.

## API

`POST /api/image-batches` acepta un documento o un envoltorio:

```json
{
  "document": [
    {"ID": 1, "Titulo": "Ejemplo", "Descripcion": "Una ficha de ejemplo", "Prompt": "A forest"}
  ],
  "source_filename": "coleccion.json",
  "settings": {"engine": "comfy", "model": "checkpoint.safetensors"}
}
```

La respuesta contiene id, chat, count y existing. `GET /api/image-batches` devuelve títulos, ID de colección, descripciones compuestas, propiedades adicionales y progreso. El ID interno del trabajo se mantiene separado del ID visible de colección.

## Activación y estado de validación

La actualización requiere cargar la versión nueva del servidor. La adaptación de metadatos existentes conserva imágenes, prompts, negativos, semillas y estado de cola; no regenera resultados. El ejemplo genérico está en `MatrixStudio/assets/collection-example.json` y se descarga desde la interfaz.

Esta revisión queda pendiente de pruebas funcionales, visuales y de GPU. No se ejecutaron pruebas para este cambio.

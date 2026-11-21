# Galería y álbumes de figuritas

**Mi galería → Álbumes JSON** agrupa cada lote importado en un álbum. La portada usa hasta cuatro imágenes terminadas y muestra el progreso de la colección. **Ver álbum de figuritas**, en Lotes JSON, abre directamente el álbum correspondiente.

Dentro del álbum, las tarjetas mantienen el orden del archivo y muestran su número de Pokédex o posición. Las entradas pendientes conservan su hueco con su nombre y estado; las eliminadas aparecen como «En papelera». No se generan ni duplican imágenes para construir el álbum.

**Todos los resultados** muestra conjuntamente los resultados de los motores. La galería aprovecha el ancho disponible y utiliza dos columnas en pantallas pequeñas, tres desde 960 px, cuatro desde 1280 px y cinco desde 1680 px de ancho de navegador.

Las tarjetas muestran imagen, nombre, número cuando corresponde y motor. El botón de información o la propia imagen abre la **descripción completa**, que reúne:

- Prompt y negativo sin recortar.
- Motor, modelo, resolución, pasos, CFG y semilla.
- Fecha, álbum, posición y metadatos de numeración disponibles.
- Todos los parámetros guardados, en un desplegable.
- Las acciones habituales: descargar, reutilizar, animar y borrar, según el resultado.

Los vídeos y objetos 3D mantienen su vista previa y pueden abrir su descripción desde el botón de información. La eliminación sigue siendo inmediata y conserva Deshacer.

Este cambio es de interfaz y utiliza los lotes ya guardados; no requiere migrar archivos ni reiniciar los motores. Tras actualizar, recarga la pestaña con Ctrl + F5. Esta revisión no se ha probado funcional ni visualmente; se mantiene pendiente de validación por el usuario.

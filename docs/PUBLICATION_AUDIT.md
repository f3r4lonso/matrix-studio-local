# Auditoría de la distribución pública

Revisión realizada el 19 de noviembre de 2026 sobre una copia limpia del código.

- Se copiaron archivos permitidos de forma explícita; no se exportó el directorio de trabajo completo.
- Se eliminaron las rutas de perfil de los lanzadores y se sustituyeron por rutas relativas o variables de entorno.
- No se incluyeron bases de datos, referencias, resultados, capturas de sesiones anteriores, registros, modelos, ejecutables, DLL ni entornos.
- El análisis automático de rutas de perfiles, tokens, claves, formatos de archivo y una lista privada de identificadores no encontró coincidencias en los archivos publicables.
- Se revisó visualmente el recurso del panda y una captura nueva de una sesión vacía. Las imágenes distribuidas no contienen metadatos de generación ni EXIF.
- Pasaron 21 pruebas aisladas de la aplicación, la comprobación sintáctica de Python/JavaScript/PowerShell, el plan del instalador sin modificaciones y el diagnóstico del entorno existente.
- La copia portable arrancó en un puerto de prueba independiente, con cero conversaciones y cero resultados, usando datos fuera del árbol publicable.
- Se conservaron los avisos de licencia de las bibliotecas. Los pesos se descargan desde sus autores y no se relicencian con el código.
- El commit inicial utiliza una identidad genérica, sin el nombre o correo configurados en el equipo de trabajo. La cuenta pública que posee el repositorio sigue siendo visible en GitHub.

La revisión se limita a los archivos publicados y las comprobaciones indicadas. No constituye una reinstalación completa del stack GPU en un segundo equipo ni una garantía de calidad visual. El hardware y las limitaciones están documentados por separado.

`release-manifest.json` enumera los archivos de esta distribución y los SHA256 de sus blobs Git (texto normalizado a LF); el propio manifiesto se excluye de esa lista para evitar una referencia circular.

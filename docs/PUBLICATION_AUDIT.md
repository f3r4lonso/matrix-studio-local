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

## Actualización del 20 de noviembre de 2026

- Se añadió el catálogo de ocho checkpoints, configuración portable de rutas, compatibilidad con instalaciones anteriores y un inventario sin carga de modelos.
- Pasaron 24 pruebas aisladas, incluidos los valores del sampler rápido de Wan y la resolución de rutas antiguas/configuradas.
- Se comprobaron la sintaxis Python y PowerShell, el plan del instalador sin escrituras, la creación de configuración en una carpeta temporal, la conservación de un motor personalizado y el inventario sin motores opcionales.
- La copia pública arrancó en un puerto independiente con datos temporales, cero conversaciones y cero resultados.
- La revisión automática de privacidad incluye la lista privada de identificadores. Los pesos, DLL, motores instalados, referencias y resultados de pruebas permanecen fuera de la publicación.
- Las observaciones de vídeo se documentan con parámetros y límites de inspección; no se presentan como garantía de coreografía ni se afirma haber probado todos los modelos del catálogo.

## Revisión local de los presets de acción

- Se prepararon presets con adaptadores por arquitectura, prompts de referencia y movimiento, comprobación de componentes y descargas fijadas por revisión y SHA256.
- Se sustituyó la decodificación temporal adicional de Wan por `VAEDecode` nativo y se añadió el archivo de latentes para comparar decodificadores.
- Pasaron 28 pruebas aisladas de la copia publicable y el análisis automático de privacidad de 66 archivos.
- Esta revisión de código no certifica calidad profesional del vídeo. Las referencias y resultados de los experimentos permanecen locales.


- Verificación posterior: 29 pruebas aisladas, RIFE opcional para Wan, duración real mayor de cinco segundos y preservación de fotogramas base. La teselación espacial mantiene el intervalo temporal completo; el archivo del latente precede al VAE. Los resultados privados no se añaden a Git.

- Validación final: 33 pruebas de la copia publicable, incluidas continuación desde el último fotograma, rechazo de referencias incompatibles y montaje con duración real mayor de cinco segundos. Se mantiene la separación entre resultados privados y fuentes publicables.

## Controles de cola, galería y Forge — 20 de noviembre de 2026

Se añadieron diez pruebas de cola, incluyendo recuperación tras reinicio, reanudación sin duplicados, errores de interrupción, solicitudes propias ComfyUI, seguimiento de tareas Forge y limpieza del proceso Qwen. Pasaron 43 pruebas en la copia publicable y 40 en la instalación de trabajo. La validación real ComfyUI detuvo y reanudó una generación, mantuvo el trabajo siguiente y conservó sus semillas. Una solicitud pendiente propia se retiró sin detener un vídeo ajeno.

La galería utiliza los metadatos guardados para mostrar motor y modelo, con escape HTML y valores explícitos cuando faltan datos históricos. Se revisaron la sintaxis JavaScript y los lanzadores PowerShell. El perfil opcional Forge conserva un entorno independiente y no distribuye motores instalados ni pesos. La revisión automática de privacidad se ejecuta de nuevo antes de publicar; los resultados de pruebas, la base de datos y la configuración privada de redirección permanecen locales.

La revisión final abarcó 77 archivos publicables sin coincidencias de identificadores privados ni credenciales. Se validó la sintaxis JavaScript de ambas copias, las etiquetas de los tres motores y la compatibilidad con metadatos ausentes, además de la sintaxis y el plan sin escrituras del instalador Forge.

## Lotes JSON con recuperación

La importación añade validación completa antes de guardar, transacción SQLite, semillas persistentes, huella del lote y progreso derivado de los resultados. Los errores pausan la cola para reintentar la entrada pendiente. Pasaron 51 pruebas en la copia publicable y las comprobaciones JavaScript de carga, vista previa y envío del formato con nombre, número, Pokédex y negativo propio. No se publican archivos de lotes ni resultados personales.

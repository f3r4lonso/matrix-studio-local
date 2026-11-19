# Revisión de privacidad de la publicación

La versión pública se prepara en un directorio limpio copiando únicamente archivos de código, pruebas, manifiestos y recursos visuales revisados. No se publica el directorio de trabajo completo ni su historial local.

## Excluido

- Bases de datos, conversaciones, prompts de sesiones, referencias, resultados, montajes y papelera.
- Capturas antiguas que pudieran mostrar historial o información de la máquina.
- Pesos, ejecutables, DLL, ZIP de motores, entornos Python y dependencias descargadas.
- Configuración local de conexiones y rutas generadas durante la instalación.
- Tokens, credenciales, archivos de entorno, claves privadas y registros.
- Nombre de usuario del sistema, rutas del perfil, nombres de equipo, correo, números de serie e identificadores de hardware.

Los lanzadores se modificaron para usar rutas relativas o variables de entorno. El avatar de la distribución es genérico. El panda es un recurso generado con IA sin metadatos de generación; la captura de documentación procede de una sesión vacía. Se conservan los avisos y autores públicos de bibliotecas de terceros porque forman parte de sus licencias, no de una sesión privada.

## Auditoría reproducible

```powershell
& $py scripts/audit_publication.py
```

Puede utilizarse una lista privada de identificadores adicionales con `--forbidden-file`; mantenla fuera del repositorio. La auditoría detecta rutas de perfiles, formatos habituales de tokens y claves, tipos de archivo no aprobados, carpetas de datos y metadatos de imágenes. No sube nada. Una revisión visual del contenido publicable complementa ese análisis; no se promete detectar todo secreto imaginable.

Los commits de la publicación se crean con nombre y correo genéricos, sin reutilizar los del entorno de trabajo. La cuenta pública propietaria y la actividad del repositorio serán visibles en GitHub. El saneamiento de los archivos no convierte la publicación en anónima ni modifica el perfil de esa cuenta.

Los datos creados tras instalar la aplicación son locales y quedan ignorados por Git. No obstante, revisa los archivos antes de futuras publicaciones: un archivo ignorado que se hubiera agregado con `git add -f` sí podría acabar en un commit.

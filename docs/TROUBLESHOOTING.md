# Solución de problemas

| Síntoma | Comprobación |
|---|---|
| `python` no existe o es otra versión | Instala Python 3.12 x64 y pasa su ejecutable con `setup-local.ps1 -Python` |
| CUDA no está disponible | Usa el Python del venv creado, verifica el driver y las ruedas cu130; ejecuta el diagnóstico |
| Faltan nodos GGUF / AnimateDiff | Revisa el checkout de las extensiones, sus dependencias y reinicia ComfyUI |
| Faltan nodos TRELLIS.2 / RIFE | Utiliza la revisión de ComfyUI fijada; algunas versiones anteriores no los incluyen |
| La UI no encuentra modelos | Ejecuta el instalador del módulo y carga `Data/matrix-studio-model-paths.yaml` al arrancar ComfyUI |
| ComfyUI ya estaba en el puerto 8188 | El proceso existente puede usar otras carpetas; reinícialo con el YAML generado o ajusta su configuración |
| SHA256 incorrecto | No se considera una descarga válida. Revisa el archivo parcial y el origen antes de volver a descargar |
| Se agota memoria o el sistema pagina mucho | Reduce resolución y fotogramas por escena; libera otros modelos. No solicites dos minutos antes de validar un plano |
| Las caras/manos se deforman | Usa una referencia clara, una acción sencilla y menos contactos. Más CFG o LoRA no garantizan corregirlo |
| Hay colores excesivos | Prueba menos CFG conservando semilla y referencia para comparar; no atribuyas una mejora a un solo valor si cambias varios ajustes |
| LightX2V rechaza los parámetros | El perfil 14B rápido exige 4 pasos/CFG 1/shift 5. Usa otro perfil para muestreo completo |
| Un montaje falla a mitad | Conserva el directorio de datos y pulsa Reanudar montaje. No cambies los parámetros del manifiesto |
| Un vídeo tarda en arrancar | Comprueba que la generación terminó. Los montajes usan H.264/yuv420p y metadatos al principio; el servidor admite peticiones Range |
| Qwen indica que falta un archivo | Configura los pesos y el ejecutable del mismo conjunto. El adaptador público no busca en el perfil del usuario ni incluye DLL de otros programas |
| Borré el vídeo y aún ocupa disco | El resultado final está en la papelera; las referencias y escenas recuperables se conservan aparte |

Los registros se crean solo en la máquina local. Antes de compartirlos, elimina prompts, rutas, nombres de archivo y cualquier dato privado. No adjuntes la base de datos ni una captura de tu historial al abrir una incidencia.

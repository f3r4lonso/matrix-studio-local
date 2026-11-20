# Liberación de VRAM entre generaciones

Studio solicita descargar modelos y liberar caché antes y después de cada trabajo, también cuando falla o se detiene. La opción **Liberar VRAM entre generaciones** está activada de forma predeterminada y se guarda en SQLite. Desactivarla permite conservar modelos cargados y reduce el coste de volver a cargarlos.

**Liberar ahora** solicita la limpieza cuando Studio no tiene una generación activa. El estado indica cuándo está limpiando y muestra advertencias si un motor está ocupado o no confirma la liberación. El siguiente trabajo de Studio espera a que termine la solicitud de limpieza.

## Comportamiento por motor

- **ComfyUI:** consulta su cola y, si está vacía, envía `/free` con `unload_models` y `free_memory`. La petición es asíncrona: se consulta `/system_stats` para distinguir una solicitud recibida de una caché CUDA reducida. El umbral de confirmación es de 256 MiB de memoria reservada por PyTorch; no significa VRAM total cero.
- **Automatic1111 / Forge:** consulta `/sdapi/v1/progress`; si el motor indica que está inactivo, solicita `/sdapi/v1/unload-checkpoint`.
- **Qwen CLI:** Studio crea un proceso por generación y espera su salida. Ese proceso ya libera su contexto al terminar. La limpieza de los otros motores inactivos antes de ejecutar Qwen evita que sus modelos retenidos compitan por memoria.

No se vacían colas, reinicia la GPU ni terminan aplicaciones externas. La memoria utilizada por Windows, el escritorio y otros programas no pertenece a Studio. Las APIs de descarga pertenecen a cada motor y no ofrecen una reserva exclusiva frente a otros clientes: usa una instancia dedicada cuando necesites coordinación estricta.

Si falla la limpieza, se conserva el resultado generado y se muestra una advertencia. Un fallo de generación mantiene las reglas de recuperación del [lote JSON](JSON_BATCHES.md). Liberar caché puede ayudar a evitar errores de memoria; no garantiza una mejora visual ni igualdad de resultados entre prompts y semillas diferentes.

## API

- `POST /api/gpu/settings` con `{"enabled": true}` o `{"enabled": false}` guarda la preferencia.
- `POST /api/gpu/release` con `{}` solicita una limpieza manual. Rechaza la petición si Studio está generando o limpiando.
- `GET /api/queue/status` incluye `gpu.enabled`, `gpu.cleaning`, `gpu.last_report` y `gpu.warning`.

La actualización requiere reiniciar el servidor Python. Esta revisión queda pendiente de pruebas funcionales y de GPU; no se ejecutaron pruebas para esta modificación. Las cifras de pruebas de versiones anteriores no validan esta función nueva.

Referencias de implementación: [ComfyUI, API del servidor](https://github.com/Comfy-Org/ComfyUI/blob/master/server.py), [Automatic1111, API](https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/master/modules/api/api.py).

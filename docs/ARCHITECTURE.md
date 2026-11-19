# Arquitectura

## Código

| Ruta | Responsabilidad |
|---|---|
| `MatrixStudio/server.py` | HTTP, límites locales, SQLite, cola, adaptadores de motores, workflows de ComfyUI y montajes |
| `MatrixStudio/index.html` | Vistas de imágenes, Wan, AnimateDiff, 3D, galería y motores |
| `MatrixStudio/assets/app.js` | Estado de UI, formularios, polling y actualización de listas sin reiniciar vídeos |
| `MatrixStudio/assets/style.css` | Estilos y diseño adaptable |
| `MatrixStudio/*_models.json` | Orígenes, destinos y SHA256 de modelos |
| `MatrixStudio/install_*.py` | Descarga reanudable y verificación de pesos |
| `MatrixStudio/evaluate_video.py` | Hoja de contacto y medidas de cambio, sin puntuar calidad |
| `MatrixStudio/tests/test_server.py` | Pruebas de API, adaptadores, datos y ensamblado de vídeo |
| `scripts/` | Infraestructura local, diagnóstico y auditoría de publicación |
| `QwenImageLocal/` | Lanzadores opcionales; los ejecutables se instalan aparte |

## API local principal

| Ruta | Acción |
|---|---|
| `GET /api/engines` | Estado y modelos de motores de imagen |
| `POST /api/engines/comfy/start` | Arranca ComfyUI local si no está disponible |
| `POST /api/settings` | Guarda URLs locales de motores |
| `GET /api/chats`, `GET /api/renders` | Historial y resultados |
| `POST /api/generate` | Generación de imágenes |
| `GET /api/video/status`, `POST /api/video/input`, `POST /api/video/generate` | Wan y referencias |
| `GET /api/animatediff/status`, `POST /api/animatediff/input`, `POST /api/animatediff/generate` | AnimateDiff |
| `GET /api/3d/status`, `POST /api/3d/input`, `POST /api/3d/generate` | TRELLIS.2 |
| `POST /api/{chats,renders}/{id}/{delete,restore}` | Borrado recuperable y restauración |
| `POST /api/renders/{id}/resume` | Reanuda un montaje fallido |

Las URLs de motores se limitan a HTTP local. El servidor escucha en loopback y comprueba Host/Origin. No incorpora autenticación pública, administración remota ni multiusuario.

## Generación

Los trabajos y sus parámetros se escriben en SQLite antes de encolarse. Un worker procesa los motores de uno en uno. ComfyUI recibe un grafo por HTTP y comunica progreso por WebSocket. El servidor recoge el archivo final desde su historial; espera brevemente si el evento de fin llega antes de que ese historial esté disponible.

Los workflows de imagen son SD 1.5/SDXL estándar. Wan 5B usa `Wan22ImageToVideoLatent` y su VAE; Wan 14B usa dos expertos, con o sin LightX2V según perfil. AnimateDiff añade el módulo temporal y, para escenas largas, FreeNoise/contexto solapado. TRELLIS.2 recorre estructura, forma y materiales con los nodos nativos de la revisión fijada de ComfyUI.

## Montajes y recuperación

`duration_seconds` acepta 0 para un clip o un entero hasta 120. `scene_prompts` es una lista de hasta 64 acciones. El planificador calcula el número de escenas con los FPS y fotogramas realmente emitidos, incluyendo la interpolación si se usa. Asigna un bloque distinto de semillas a cada vídeo del lote.

Se conserva un manifiesto con la firma de los parámetros y cada MP4 de escena. PyAV decodifica y codifica de forma secuencial, a FPS constantes, en H.264/yuv420p con metadatos al principio del archivo. Se recorta el último plano, sin bucles, relleno congelado ni cambio de velocidad. Las escenas se reutilizan solo si coincide la firma del trabajo. Tras un reinicio los trabajos pendientes se marcan como fallidos y pueden reanudarse desde la UI.

## Directorios locales

`Data/` contiene infraestructura, pesos y el YAML de rutas generado. `Runtime/` es el directorio de datos del lanzador: SQLite, referencias, resultados, papelera, registros y escenas recuperables. Ambos están excluidos de Git. Si se ejecuta `server.py` directamente sin `MATRIX_STUDIO_DATA_DIR`, los datos se crean junto al servidor; también están excluidos por patrones.

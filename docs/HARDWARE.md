# Hardware y alcance de la validación

Fecha de referencia: 19 de noviembre de 2026. Se publican únicamente características técnicas genéricas.

| Componente | Validado |
|---|---|
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU |
| VRAM | 8 GB nominales, 8151 MiB reportados por el driver |
| CPU | Intel Core i7-14650HX |
| RAM | 16 GB nominales; aproximadamente 15,6 GiB utilizables |
| OS | Windows 11 x64 |
| Driver | NVIDIA 616.92 |
| Runtime Python | 3.12.14 |
| PyTorch | 2.14.1+cu130 |
| torchvision | 0.29.1+cu130 |
| Atención | PyTorch cross-attention; no se exige xformers/flash-attn |

El script acepta Python 3.12; la microversión concreta anterior es la del equipo probado. No se publican nombre de equipo, usuario del sistema, correo, números de serie, UUID, claves del sistema, red ni listados completos del entorno.

## Qué se ha probado

- Aplicación: 21 pruebas automatizadas con API local, motores simulados y MP4 reales de prueba. Incluyen dos montajes de 120 segundos, 960 fotogramas a 8 fps cada uno, semillas no solapadas y recuperación tras fallo.
- Wan 14B Q3 + LightX2V: vídeo IA de 33 fotogramas, 480 × 320, 16 fps, aproximadamente 163 segundos de cálculo en la primera ejecución medida.
- Wan 5B Q5: dos escenas de 121 fotogramas a 640 × 384; montaje IA de 10 segundos, 240 fotogramas, 24 fps. Un primer plano tardó unos 223 segundos.
- Wan 5B con referencia distinta: dos escenas de hasta 73 fotogramas a 640 × 416, CFG 3.5, shift 5 y 20 pasos; montaje IA de 6 segundos, 144 fotogramas a 24 fps. Un plano medido tardó unos 132 segundos.
- AnimateDiff: MP4 desde texto y desde imagen, y un conjunto de nueve pruebas cortas de personas. RIFE se ejecutó con salida de 46 fotogramas a 24 fps en esos ensayos anteriores.
- TRELLIS.2: GLB con color por vértices y con PBR, 512³, 8 pasos y unas 30.000 caras objetivo.

La publicación portable se verifica por separado con pruebas y una sesión vacía. No se ha descargado ni reinstalado de nuevo todo el stack GPU en una segunda máquina para certificar el instalador de extremo a extremo. Qwen y Automatic1111/Forge son adaptadores opcionales; una instalación limpia de esos motores no se ha vuelto a validar en esta publicación.

## Qué no se puede garantizar

El consumo depende de resolución, fotogramas por escena, modelo, precisión, pasos, atención, procesos abiertos y versión del driver. Las pruebas cortas no acreditan que cualquier configuración funcione en 8 GB. El tamaño 1280 × 704 está disponible para 5B por compatibilidad con su ejemplo nativo, pero no se ha medido aquí. No se generó un vídeo IA completo de 120 segundos: su duración se verifica en el ensamblador y el camino de GPU se valida con montajes cortos.

Los vídeos de pelea siguen mostrando errores de contacto, manos o fusiones de cuerpos. Más CFG, pasos, resolución, interpolación o LoRA no garantizan eliminar esos errores. No hay control de pose ni referencia de movimiento en el flujo actual.

## Recomendaciones prácticas

Empieza por una escena y el perfil equilibrado. Una referencia limpia ayuda a evaluar el movimiento sin añadir defectos de partida. El montaje mantiene la referencia original entre planos para evitar encadenar la degradación; no garantiza identidad perfecta. Reserva espacio para cachés y resultados además de los pesos de [MODELS.md](MODELS.md). Dos minutos de contenido pueden requerir más de una hora de cálculo local.

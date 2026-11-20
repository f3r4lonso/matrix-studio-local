# Pruebas de movimiento: sparring básico

Pruebas locales del 20 de noviembre de 2026 con RTX 5060 Laptop de 8 GB y 16 GB de RAM. Se utilizó una misma referencia de dos adultos con camiseta roja/azul, guantes y fondo de estudio; plano lateral fijo con cuerpos separados. Son observaciones sobre esta escena y semilla, no una clasificación general de modelos.

| Prueba | Modelo | Ajustes | Duración codificada | Observación |
|---|---|---|---|---|
| Base | Wan 2.2 I2V 14B Q3_K_S + LightX2V | 640×384, 81 frames, 16 fps, 4 pasos, CFG 1, shift 5, Euler/simple, semilla 7331 | 5,0625 s | Dos jabs visibles y bloqueos; pausa larga y sin el contraataque solicitado |
| Alternativa | Wan 2.2 TI2V 5B Q5_K_M | 640×384, 121 frames, 24 fps, 30 pasos, CFG 5, shift 8, UniPC/simple, semilla 7331 | 5,0417 s | Más intercambio, pero guantes duplicados y trayectorias menos consistentes |
| Selección provisional | 14B, mismos ajustes de la base | Prompt más corto: tres jabs y bloqueo; misma referencia y semilla | 5,0625 s | Más actividad y recuperación de guardia; persisten estelas y un jab adicional |

Las ejecuciones de ComfyUI de las dos primeras pruebas tardaron aproximadamente 297 y 317 segundos. La tercera tardó unos 261 segundos medidos desde la aplicación; los tiempos de aplicación incluyen esperas y no son directamente comparables con tiempos internos del motor.

Se decodificaron todos los fotogramas y se inspeccionaron 24 muestras por clip. No se realizó una revisión continua de reproducción ni una evaluación ciega. La selección es un candidato para sparring básico; no demuestra contacto físicamente correcto ni una coreografía exacta. No se publican las referencias ni los vídeos privados.

Prompt de prueba reproducible para imagen inicial:

> Wide side view, full bodies visible, two adult martial artists wearing red and blue training shirts and boxing gloves, standing apart in guard, plain gray studio, fixed camera, clear limbs, soft even lighting.

Prompt de vídeo simplificado a partir de esa referencia:

> Fixed side camera. The adult fighter in red throws three slow straight jabs toward the blue fighter's raised gloves. Blue blocks each jab. Red returns to guard between punches. Both remain standing apart, full bodies visible, clear controlled training movements.

Para comparar cambios: conserva referencia, resolución y semilla; cambia una variable por prueba. Empieza con una acción repetida y una cámara fija. Evalúa continuidad de brazos, separación de cuerpos, retorno a guardia y duración. A CFG 1, el sampler de ComfyUI omite la rama negativa; no confíes en ampliar el prompt negativo para corregir esta configuración.

El flujo rápido 14B usa Euler y el perfil de calidad usa UniPC. El flujo oficial 5B proporciona una referencia de 20 pasos, CFG 5 y shift 8; los 30 pasos de esta prueba no demostraron una mejora de contacto. Un siguiente paso sería integrar control de movimiento/pose, que todavía no está disponible en este adaptador.

Fuentes técnicas: [Wan 2.2 en ComfyUI](https://docs.comfy.org/tutorials/video/wan/wan2_2), [flujo oficial 5B](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_wan2_2_5B_ti2v.json), [LightX2V y sus límites](https://huggingface.co/lightx2v/Wan2.2-Lightning), [implementación del sampler](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy/samplers.py). Las variantes anunciadas como «uncensored» no se instalaron ni probaron en esta comparación; esa etiqueta no demuestra mejores golpes o anatomía.

## Corrección de decodificación y adaptadores de acción

El flujo anterior usaba `VAEDecodeTiled` con bloques temporales de 16 fotogramas y solapamiento de 4. Aparecieron estelas y saltos de exposición con ese patrón. La [incidencia del mantenedor de ComfyUI](https://github.com/Comfy-Org/ComfyUI/issues/7116) explica por qué la decodificación temporal adicional puede causar parpadeo en Wan, cuyo VAE ya procesa internamente la secuencia por bloques.

Los flujos Wan 5B y 14B usan `VAEDecode` nativo hasta 512² píxeles. Por encima de esa superficie, se usan teselas espaciales de 256 con solapamiento 64 y `temporal_size=128`: el bloque temporal completo cubre los hasta 121 fotogramas admitidos. Así se reduce la presión de VRAM sin volver a dividir el tiempo. La decodificación nativa a 768² agotó la memoria práctica de esta GPU de 8 GB; se recuperó el latente sin repetir el sampler. Una comparación reutilizó el mismo resultado del sampler desde la caché de ComfyUI y cambió únicamente el decodificador: se estabilizó la exposición del retrato; el contacto lento del guante seguía siendo insuficiente. La corrección de decodificación no garantiza una coreografía mejor. Se archiva también el latente con `SaveLatent` en la carpeta de resultados de ComfyUI para permitir comparaciones posteriores sin repetir el muestreo.

`action_adapters.json` fija revisiones, tamaños, licencias y SHA256 de cinco archivos LoRA. El instalador `MatrixStudio/install_action_adapters.py` descarga únicamente esos adaptadores, sin nuevos modelos base. `action_presets.json` contiene los prompts de imagen inicial y movimiento y los parámetros de cada receta. La interfaz agrupa las opciones técnicas en secciones plegadas.

| Uso | Modelo y VAE | Adaptadores | Estado y límites |
|---|---|---|---|
| Movimiento general | Wan 2.2 I2V 14B + `wan_2.1_vae` | Slow-Mo Fix high/low, 1.0, cuatro pasos | El autor propone reducir el efecto de cámara lenta. No controla por sí solo una pelea. |
| Forma individual | Mismo 14B y VAE | Slow-Mo Fix + KungFu high/low, 0.8 | Combinación experimental: puño, giro y patada legibles en una referencia; no demuestra contacto entre dos luchadores. |
| Impacto en retrato | Wan 2.2 TI2V 5B + `wan2.2_vae` | Aether Punch, 1.0 | La ficha recomienda 768², 121 frames, 24 fps, 20 pasos y CFG 5. Las primeras pruebas a 512² mostraron contacto lento, sin una reacción convincente. |

Fuentes de las recetas: [Slow-Mo Fix](https://huggingface.co/rzgar/Wan2.2_I2V_LightX2V_Slow-Mo_Fix), [KungFu](https://huggingface.co/joyfox/Wan2.2-I2V-KungFu) y [Aether Punch](https://huggingface.co/joachimsallstrom/Aether_Punch_Wan22_5b_i2v_LoRA). La combinación de KungFu con aceleración es una prueba propia; difiere del shift 8 y la intensidad 1 indicados por el autor de KungFu. No se presenta como una receta oficial ni como una garantía de calidad profesional.


## Receta de sparring comprobada y suavizado

La receta «Boxeo · intercambio probado» usa el 14B existente, VAE Wan 2.1, pareja Slow-Mo Fix a intensidad 1, Euler/simple, 4 pasos, CFG 1 y shift 5. Plano medio 832 × 416, 81 fotogramas base a 16 fps, semilla 1742. RIFE 4.26 a 2× produce 161 fotogramas a 32 fps y 5,03125 segundos reales. La interpolación suaviza transiciones y no inventa golpes físicamente correctos. El negativo no interviene con CFG 1.

Se compararon el mismo encuadre a 640 × 320 y 832 × 416; se seleccionó el segundo por detalle y legibilidad. El movimiento observado incluye puños a la guardia, bloqueo y respuesta del boxeador azul. Persisten contactos prolongados y un aspecto sintético: este resultado se registra como mejor prueba local, sin certificar calidad profesional. Se conservaron los prompts, semillas, referencia, hashes, latentes y hojas de fotogramas en el laboratorio privado. Las imágenes de entrada y los vídeos no se incluyen en esta publicación.

La referencia exacta importa tanto como el prompt: dos adultos ya enfrentados y a distancia de golpe, guantes rojos y azules claramente separados, cámara fija y plano medio. Cambiar la imagen cambia la coreografía aunque se mantenga la semilla. «Reutilizar» conserva ahora la semilla y el suavizado. El latente se guarda antes de decodificar, como dependencia explícita del grafo.

La prueba adicional de Aether Punch a los 768² recomendados por el autor tampoco logró una reacción convincente. La interfaz lo marca como experimental; no es la receta seleccionada de pelea.


## Continuación y montaje de la pelea seleccionada

La referencia Qwen se regeneró con textura de piel y guantes, iluminación lateral y gimnasio oscuro. El primer tramo usa la receta anterior; el segundo parte del último fotograma decodificado del primero, con semilla 1743 y un prompt de retirada, jab y contraataque. Ambos tramos duran 5,03125 s a 32 fps con RIFE; sus 81 fotogramas originales por tramo proceden de generación a 16 fps. Cada tramo tardó aproximadamente 316 segundos en la aplicación.

El montaje conserva esos originales, descarta los intermedios RIFE y omite el fotograma de enlace repetido del segundo tramo. Reproduce los 161 originales resultantes a 32 fps: 5,03125 segundos de acción a velocidad 2×. No se añaden pausas, fotogramas congelados ni audio. Se revisaron las seis hojas con todos los fotogramas del montaje. La API produjo exactamente los mismos bytes que el montaje revisado. Mejora el acabado y el ritmo; persisten pequeñas imprecisiones de guantes y contacto, por lo que no se certifica calidad cinematográfica profesional.

Desde la interfaz:

1. Selecciona «Boxeo · intercambio probado», utiliza una referencia fotográfica y genera el primer vídeo.
2. Pulsa «Continuar boxeo» en su resultado; espera al segundo vídeo.
3. En la continuación pulsa «Montar pelea 2×». La app verifica que la imagen de arranque coincide con el último fotograma del primero y guarda el montaje como un resultado nuevo descargable.

Las rutas `/api/video/continue` y `/api/video/assemble` aceptan identificadores de resultados locales. Rechazan fuentes incompletas, montajes previos, FPS/resoluciones incompatibles y continuaciones con otra referencia. La edición usa CPU y no descarga pesos nuevos. Los resultados montados no ofrecen el botón genérico de regenerar, porque necesitan sus dos fuentes.

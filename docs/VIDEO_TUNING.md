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

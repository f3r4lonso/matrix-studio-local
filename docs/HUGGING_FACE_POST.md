# Matrix Studio Local: imágenes, vídeo y 3D desde una interfaz local

**[Español](HUGGING_FACE_POST.md) | [English](HUGGING_FACE_POST.en.md)**

He preparado Matrix Studio Local, una interfaz web con conversaciones y galería para conectar varios motores de generación en el propio equipo.

**Código e instalación:** https://github.com/f3r4lonso/matrix-studio-local

Incluye ComfyUI para imágenes SD/SDXL, Wan 2.2 5B/14B para vídeo desde imagen, AnimateDiff con Motion LoRA y RIFE, y TRELLIS.2 para exportar objetos GLB. También hay adaptadores opcionales para Automatic1111/Forge y Qwen mediante stable-diffusion.cpp.

Los vídeos pueden montarse por escenas hasta 120 segundos, con un guion por planos, semillas diferentes y recuperación de las escenas completadas si falla un trabajo. Son escenas nuevas con cortes: no un único plano continuo ni un clip repetido en bucle.

La configuración de referencia utiliza una RTX 5060 Laptop de 8 GB, Intel i7-14650HX y 16 GB de RAM, con Windows 11, Python 3.12 y PyTorch CUDA 13.0. El repositorio documenta los commits, paquetes, pesos y hashes necesarios para montar la infraestructura local.

Es importante distinguir funcionamiento y calidad: se generaron montajes IA cortos de 6 y 10 segundos y se verificó la exportación de 120 segundos con pruebas técnicas. No se ha renderizado un vídeo IA completo de dos minutos como validación. Persisten errores de anatomía y contacto entre personas; los ajustes no garantizan una coreografía realista. Un montaje largo puede tardar más de una hora en esta GPU.

Se publica código, pruebas e instrucciones, sin modelos, conversaciones, referencias ni resultados privados. Los pesos se descargan desde sus distribuidores y mantienen sus propias licencias.

El objetivo es ofrecer una base local que pueda inspeccionarse y reproducirse, sin depender de una API de generación de pago. La instalación limpia y los límites de validación están explicados en el README.

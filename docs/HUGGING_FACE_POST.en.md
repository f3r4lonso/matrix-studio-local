# Matrix Studio Local: images, video, and 3D from a local interface

**[Español](HUGGING_FACE_POST.md) | [English](HUGGING_FACE_POST.en.md)**

I've put together Matrix Studio Local, a web interface with conversations and a gallery that connects several generation engines running on your own computer.

**Code and installation:** [GitHub repository](https://github.com/f3r4lonso/matrix-studio-local) · [English README](https://github.com/f3r4lonso/matrix-studio-local/blob/main/README.en.md)

It includes ComfyUI for SD/SDXL images, Wan 2.2 5B/14B for image-to-video, AnimateDiff with Motion LoRA and RIFE, and TRELLIS.2 for exporting GLB objects. Optional adapters support Automatic1111/Forge and Qwen through stable-diffusion.cpp.

Videos can be assembled into montages up to 120 seconds, with a shot-by-shot script, different seeds, and recovery of completed scenes if a job fails. These are newly generated scenes joined with cuts, rather than a single continuous shot or a repeated clip.

The reference setup uses an RTX 5060 Laptop with 8 GB VRAM, an Intel i7-14650HX, and 16 GB RAM, running Windows 11, Python 3.12, and PyTorch CUDA 13.0. The repository documents the commits, packages, weights, and hashes needed to set up the local infrastructure.

Functionality and visual quality have different validation limits: short AI montages of 6 and 10 seconds were generated, and 120-second exports were checked with technical tests. A complete two-minute AI video has not been rendered for validation. Anatomy and body-contact errors remain; settings do not guarantee realistic choreography. A long montage can take more than an hour on this GPU.

The release includes code, tests, and instructions, without models, private conversations, reference images, or generated outputs. Weights are downloaded from their distributors and retain their own licenses.

The aim is to provide an inspectable local foundation that can be reproduced without relying on a paid generation API. The README explains clean installation and the limits of validation. Documentation is available in Spanish and English; the current application interface uses Spanish labels.

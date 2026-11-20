"""Matrix Studio: chat local para los motores de Stability Matrix."""
import asyncio
import base64
import json
import io
import math
import hashlib
from fractions import Fraction
import os
import random
import sqlite3
import struct
import sys
import time
import uuid
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_paths import project_asset
import av
from aiohttp import web
from PIL import Image, ImageOps, UnidentifiedImageError

APP = Path(__file__).resolve().parent
ROOT = APP.parent
DATA = Path(os.environ.get('MATRIX_STUDIO_DATA_DIR', str(APP)))
OUTPUT = DATA / 'outputs'
OUTPUT.mkdir(parents=True, exist_ok=True)
INPUTS = DATA / 'inputs'
INPUTS.mkdir(parents=True, exist_ok=True)
WAN_MODELS = json.loads((APP / 'wan_models.json').read_text())
WAN_NAMES = {m['key']: Path(m['file']).name for m in WAN_MODELS}
TRELLIS_MODELS = json.loads((APP / 'trellis_models.json').read_text())
TRELLIS_NAMES = {m['key']: Path(m['file']).name for m in TRELLIS_MODELS}
ANIMATEDIFF_MODELS = json.loads((APP / 'animatediff_models.json').read_text())
ANIMATEDIFF_NAMES = {m['key']: Path(m['file']).name for m in ANIMATEDIFF_MODELS}
WAN5B_MODELS = json.loads((APP / 'wan5b_models.json').read_text())
WAN5B_NAMES = {m['key']: Path(m['file']).name for m in WAN5B_MODELS}
VIDEO_PROJECTS = DATA / 'video_projects'
PORT = int(os.environ.get('MATRIX_STUDIO_PORT', '7880'))
DB = sqlite3.connect(DATA / 'studio.db')
DB.row_factory = sqlite3.Row
DB.executescript('''
CREATE TABLE IF NOT EXISTS chats (id TEXT PRIMARY KEY, title TEXT, created REAL);
CREATE TABLE IF NOT EXISTS renders (id TEXT PRIMARY KEY, chat_id TEXT, prompt TEXT,
 params TEXT, status TEXT, detail TEXT, image TEXT, created REAL);
''')
DB.commit()
for table, column in (('chats', 'deleted'), ('renders', 'image_deleted')):
    if column not in {row['name'] for row in DB.execute(f'PRAGMA table_info({table})')}:
        DB.execute(f'ALTER TABLE {table} ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0')
DB.commit()
DEFAULT = {'comfy': 'http://127.0.0.1:8188', 'automatic': 'http://127.0.0.1:7860'}
CONFIG_FILE = DATA / 'engines.json'
CONFIG = {**DEFAULT, **(json.loads(CONFIG_FILE.read_text()) if CONFIG_FILE.exists() else {})}
QWEN = Path(os.environ.get('MATRIX_STUDIO_QWEN_DIR', str(ROOT / 'QwenImageLocal')))
QFILES = [
    Path(os.environ.get('MATRIX_STUDIO_QWEN_CLI', str((QWEN / 'engine' if 'MATRIX_STUDIO_QWEN_DIR' in os.environ else project_asset('sd_cpp_engine')) / 'sd-cli.exe'))),
    Path(os.environ.get('MATRIX_STUDIO_QWEN_MODEL', str(project_asset('qwen_model')))),
    Path(os.environ.get('MATRIX_STUDIO_QWEN_ENCODER', str(project_asset('qwen_encoder')))),
    Path(os.environ.get('MATRIX_STUDIO_QWEN_VAE', str(project_asset('qwen_vae')))),
]
CUDA = Path(os.environ.get('MATRIX_STUDIO_CUDA_DIR', str(QWEN / 'engine' if 'MATRIX_STUDIO_QWEN_DIR' in os.environ else project_asset('cuda_runtime'))))



def rows(sql, args=()):
    return [dict(r) for r in DB.execute(sql, args)]


def update(rid, **values):
    DB.execute('UPDATE renders SET ' + ','.join(f'{k}=?' for k in values) + ' WHERE id=?', (*values.values(), rid))
    DB.commit()


def local_url(value):
    parsed = urlparse(value)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise ValueError('Usa una dirección local como http://127.0.0.1:8188')
    return value.rstrip('/')


@web.middleware
async def boundary(request, handler):
    if request.host not in (f'127.0.0.1:{PORT}', f'localhost:{PORT}'):
        raise web.HTTPForbidden()
    if request.method != 'GET' and request.headers.get('Origin') not in (None, f'http://127.0.0.1:{PORT}', f'http://localhost:{PORT}'):
        raise web.HTTPForbidden()
    try:
        return await handler(request)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return web.json_response({'error': str(exc)}, status=400)


async def api(session, url, payload=None, timeout=10):
    async with session.request('POST' if payload is not None else 'GET', url, json=payload,
                               timeout=aiohttp.ClientTimeout(total=timeout), allow_redirects=False) as response:
        if response.status != 200:
            raise ValueError(f'Motor: HTTP {response.status}. {(await response.text())[:500]}')
        return await response.json()


async def engines(request):
    session = request.app['session']
    async def check(key, path):
        try:
            data = await api(session, CONFIG[key] + path, timeout=2)
            if key == 'comfy':
                models = data['CheckpointLoaderSimple']['input']['required']['ckpt_name'][0]
                return {'id': key, 'ready': bool(models), 'models': models, 'detail': 'Conectado' if models else 'Sin checkpoints instalados'}
            return {'id': key, 'ready': True, 'models': [m['title'] for m in data], 'detail': 'Conectado'}
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, KeyError):
            return {'id': key, 'ready': False, 'models': [], 'detail': 'Sin conexión'}
    result = await asyncio.gather(check('comfy', '/object_info/CheckpointLoaderSimple'), check('automatic', '/sdapi/v1/sd-models'))
    missing = [p.name for p in QFILES + [CUDA / 'cudart64_12.dll'] if not p.exists()]
    result.insert(1, {'id': 'qwen', 'ready': not missing, 'models': ['Qwen Image 2.1 Turbo'],
                      'detail': 'Listo para generar' if not missing else 'Faltan archivos: ' + ', '.join(missing)})
    return web.json_response({'engines': result, 'config': CONFIG})


async def settings(request):
    data = await request.json()
    validated = {key: local_url(data[key]) for key in DEFAULT}
    CONFIG_FILE.write_text(json.dumps(validated, indent=2), encoding='utf-8')
    CONFIG.update(validated)
    return web.json_response({'ok': True})


async def boot_comfy(request):
    app = request.app
    process = app.get('comfy_process')
    if process and process.returncode is None:
        return web.json_response({'detail': 'ComfyUI está arrancando. Actualiza la conexión en unos segundos.'})
    try:
        await api(app['session'], CONFIG['comfy'] + '/system_stats', timeout=2)
        return web.json_response({'detail': 'ComfyUI ya está conectado.'})
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        pass
    if CONFIG['comfy'] != DEFAULT['comfy']:
        raise ValueError('Para un puerto personalizado, inicia ComfyUI desde Stability Matrix.')
    folder = Path(os.environ.get('MATRIX_STUDIO_COMFY_DIR', str(project_asset('comfy_engine'))))
    log = open(DATA / 'comfyui.log', 'a', encoding='utf-8')
    try:
        app['comfy_process'] = await asyncio.create_subprocess_exec(str(Path(os.environ.get('MATRIX_STUDIO_COMFY_PYTHON', str(folder / 'venv/Scripts/python.exe')))),
            'main.py', '--listen', '127.0.0.1', '--port', '8188', '--use-pytorch-cross-attention',
            *(['--extra-model-paths-config', str(ROOT / 'Data/matrix-studio-model-paths.yaml')] if (ROOT / 'Data/matrix-studio-model-paths.yaml').is_file() else []),
            cwd=folder, stdout=log, stderr=log)
    finally:
        log.close()
    return web.json_response({'detail': 'Iniciando ComfyUI. La primera carga puede tardar; pulsa Actualizar conexión.'})


async def chats(request):
    return web.json_response(rows('SELECT * FROM chats WHERE deleted=0 ORDER BY created DESC'))


async def renders(request):
    chat = request.query.get('chat')
    result = rows('SELECT * FROM renders WHERE chat_id=? ORDER BY created', (chat,)) if chat else rows('SELECT * FROM renders WHERE image_deleted=0 ORDER BY created DESC')
    for row in result:
        row['params'] = json.loads(row['params'])
        if row['image_deleted']:
            row.update(image=None, status='deleted', detail='Imagen eliminada de la galería.')
    return web.json_response(result)


async def delete_item(request):
    kind, item = request.match_info['kind'], request.match_info['id']
    restore = request.match_info['action'] == 'restore'
    if kind == 'chats':
        if not rows('SELECT id FROM chats WHERE id=?', (item,)):
            raise web.HTTPNotFound()
        if not restore and rows("SELECT id FROM renders WHERE chat_id=? AND status IN ('queued','running')", (item,)):
            return web.json_response({'error': 'Espera a que termine la generación antes de borrar este chat.'}, status=409)
        DB.execute('UPDATE chats SET deleted=? WHERE id=?', (0 if restore else 1, item))
    else:
        found = rows('SELECT * FROM renders WHERE id=?', (item,))
        if not found or found[0]['status'] != 'done':
            raise web.HTTPNotFound()
        suffix = {'video': '.mp4', 'mesh': '.glb'}.get(json.loads(found[0]['params']).get('kind'), '.png')
        source = OUTPUT / (item + suffix)
        trash = DATA / 'trash'
        trash.mkdir(exist_ok=True)
        recycled = trash / source.name
        if restore and recycled.exists():
            recycled.replace(source)
        elif not restore and source.exists():
            source.replace(recycled)
        DB.execute('UPDATE renders SET image_deleted=? WHERE id=?', (0 if restore else 1, item))
    DB.commit()
    return web.json_response({'ok': True})


async def generate(request):
    data = await request.json()
    prompt = str(data.get('prompt', '')).strip()
    if not prompt or len(prompt) > 12000:
        raise ValueError('Escribe un prompt de entre 1 y 12000 caracteres.')
    engine = data.get('engine')
    if engine not in ('comfy', 'qwen', 'automatic'):
        raise ValueError('Selecciona un motor.')
    p = {key: data.get(key, default) for key, default in {'engine': engine, 'model': '', 'negative': '',
        'width': 512, 'height': 512, 'steps': 8, 'cfg': 1, 'seed': -1}.items()}
    for key in ('width', 'height', 'steps', 'seed'):
        p[key] = int(p[key])
    p['cfg'] = float(p['cfg'])
    if any(p[k] < 256 or p[k] > 2048 or p[k] % 32 for k in ('width', 'height')):
        raise ValueError('Las dimensiones deben ser múltiplos de 32 entre 256 y 2048.')
    if not 1 <= p['steps'] <= 150 or not 0 <= p['cfg'] <= 30 or not -1 <= p['seed'] <= 2147483647:
        raise ValueError('Ajustes fuera de rango.')
    count = data.get('count', 1)
    if type(count) is not int or not 1 <= count <= 8:
        raise ValueError('Elige entre 1 y 8 imágenes por generación.')
    seeds = random.sample(range(2147483648), count) if p['seed'] == -1 else [(p['seed'] + i) % 2147483648 for i in range(count)]
    cid = data.get('chat')
    if cid and not rows('SELECT id FROM chats WHERE id=? AND deleted=0', (cid,)):
        raise ValueError('Conversación no encontrada.')
    ids = []
    with DB:
        if not cid:
            cid = uuid.uuid4().hex
            DB.execute('INSERT INTO chats (id,title,created) VALUES (?,?,?)', (cid, prompt[:55], time.time()))
        for i, seed in enumerate(seeds):
            rid = uuid.uuid4().hex
            params = {**p, 'seed': seed, 'batch_index': i + 1, 'batch_count': count}
            DB.execute('INSERT INTO renders (id,chat_id,prompt,params,status,detail,image,created) VALUES (?,?,?,?,?,?,?,?)',
                (rid, cid, prompt, json.dumps(params), 'queued', f'En cola · imagen {i + 1} de {count}', None, time.time()))
            ids.append(rid)
    for rid in ids:
        request.app['queue'].put_nowait(rid)
    return web.json_response({'id': ids[0], 'ids': ids, 'chat': cid, 'count': count})


def workflow(p, prompt):
    return {
        '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': p['model']}},
        '2': {'class_type': 'CLIPTextEncode', 'inputs': {'text': prompt, 'clip': ['1', 1]}},
        '3': {'class_type': 'CLIPTextEncode', 'inputs': {'text': p['negative'], 'clip': ['1', 1]}},
        '4': {'class_type': 'EmptyLatentImage', 'inputs': {'width': p['width'], 'height': p['height'], 'batch_size': 1}},
        '5': {'class_type': 'KSampler', 'inputs': {'seed': p['seed'], 'steps': p['steps'], 'cfg': p['cfg'],
            'sampler_name': 'euler', 'scheduler': 'normal', 'denoise': 1, 'model': ['1', 0],
            'positive': ['2', 0], 'negative': ['3', 0], 'latent_image': ['4', 0]}},
        '6': {'class_type': 'VAEDecode', 'inputs': {'samples': ['5', 0], 'vae': ['1', 2]}},
        '7': {'class_type': 'SaveImage', 'inputs': {'images': ['6', 0], 'filename_prefix': 'MatrixStudio/image'}}}


async def video_status(request):
    models = []
    for model in WAN_MODELS:
        target = ROOT / 'Data/Models' / model['folder'] / Path(model['file']).name
        partial = target.with_suffix(target.suffix + '.part')
        models.append({'name': target.name, 'ready': target.exists(), 'downloaded': partial.stat().st_size if partial.exists() else 0})
    ready14 = all(m['ready'] for m in models)
    ready5 = all((ROOT / 'Data/Models' / m['folder'] / Path(m['file']).name).is_file() for m in WAN5B_MODELS) and models[2]['ready']
    return web.json_response({'ready': ready14 or ready5, 'models': models, 'default_family': 'wan5b' if ready5 else 'wan14b',
        'families': [{'id': 'wan5b', 'ready': ready5}, {'id': 'wan14b', 'ready': ready14}]})


async def video_input(request):
    reader = await request.multipart()
    part = await reader.next()
    if part is None or part.name != 'image':
        raise ValueError('Selecciona una imagen PNG, JPG o WebP.')
    content = bytearray()
    while chunk := await part.read_chunk():
        content.extend(chunk)
        if len(content) > 20 * 1024 * 1024:
            raise ValueError('La imagen debe ocupar menos de 20 MB.')
    try:
        with Image.open(io.BytesIO(content)) as source:
            image = ImageOps.exif_transpose(source).convert('RGBA')
            name = uuid.uuid4().hex + '.png'
            image.save(INPUTS / name)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('No se pudo leer la imagen.') from exc
    return web.json_response({'name': name, 'url': '/inputs/' + name})


def resolve_input(data):
    source_id = str(data.get('render_id', ''))
    name = str(data.get('input_image', ''))
    if source_id:
        found = rows("SELECT * FROM renders WHERE id=? AND status='done' AND image_deleted=0", (source_id,))
        if not found or json.loads(found[0]['params']).get('kind') in ('video', 'mesh'):
            raise ValueError('La imagen de la galería ya no está disponible.')
        source = OUTPUT / (found[0]['id'] + '.png')
        name = uuid.uuid4().hex + '.png'
        (INPUTS / name).write_bytes(source.read_bytes())
    if len(name) != 36 or not name.endswith('.png') or any(c not in '0123456789abcdef' for c in name[:-4]) or not (INPUTS / name).is_file():
        raise ValueError('Sube una imagen o elígela desde la galería.')
    return name


async def generate_video(request):
    data = await request.json()
    prompt = str(data.get('prompt', '')).strip()
    if not prompt or len(prompt) > 12000:
        raise ValueError('Describe el movimiento del vídeo (hasta 12000 caracteres).')
    name = resolve_input(data)
    ready5 = all((ROOT / 'Data/Models' / m['folder'] / Path(m['file']).name).is_file() for m in WAN5B_MODELS)
    family = str(data.get('family', 'wan5b' if ready5 else 'wan14b'))
    if family not in ('wan5b', 'wan14b'):
        raise ValueError('Selecciona Wan 5B o Wan 14B.')
    profile = str(data.get('profile', 'balanced'))
    if profile not in ('fast', 'balanced', 'quality'):
        raise ValueError('Selecciona el perfil rápido, equilibrado o de calidad.')
    steps = {'fast': 10 if family == 'wan5b' else 4, 'balanced': 20, 'quality': 50 if family == 'wan5b' else 40}[profile]
    p = {'kind': 'video', 'engine': 'comfy', 'family': family, 'model': 'Wan 2.2 5B · Q5_K_M' if family == 'wan5b' else 'Wan 2.2 I2V 14B · Q3_K_S', 'input_image': name,
         'width': int(data.get('width', 640)), 'height': int(data.get('height', 384)),
         'frames': int(data.get('frames', 121 if family == 'wan5b' else 81)), 'fps': 24 if family == 'wan5b' else 16, 'profile': profile, 'steps': steps,
         'cfg': 5.0 if family == 'wan5b' else 1.0 if profile == 'fast' else 3.5,
         'shift': 5.0 if family == 'wan5b' else 5.0 if profile == 'fast' else 3.0,
         'negative': str(data.get('negative', 'blurry, static, distorted, low quality')), 'seed': int(data.get('seed', -1))}
    for key, cast in (('steps', int), ('cfg', float), ('shift', float)):
        if key in data:
            value = cast(data[key])
            if family == 'wan14b' and profile == 'fast' and value != p[key]:
                raise ValueError('LightX2V requiere 4 pasos, CFG 1 y shift 5. Cambia de perfil para ajustar el muestreo.')
            p[key] = value
    if not 4 <= p['steps'] <= 60 or not 1 <= p['cfg'] <= 8 or not 1 <= p['shift'] <= 12:
        raise ValueError('Pasos: 4–60. CFG: 1–8. Shift: 1–12.')
    maximum = 1280 if family == 'wan5b' else 832
    if any(p[k] < 128 or p[k] > maximum or p[k] % 16 for k in ('width', 'height')) or not 5 <= p['frames'] <= 121 or (p['frames'] - 1) % 4:
        raise ValueError(f'Resolución: múltiplos de 16 entre 128 y {maximum}. Fotogramas: 4n+1 entre 5 y 121.')
    if not -1 <= p['seed'] <= 2147483647:
        raise ValueError('La semilla debe estar entre -1 y 2147483647.')
    if family == 'wan5b' and any(p[k] % 32 for k in ('width', 'height')):
        raise ValueError('Wan 5B necesita dimensiones múltiplos de 32.')
    required = WAN5B_MODELS + [m for m in WAN_MODELS if m['key'] == 'text'] if family == 'wan5b' else WAN_MODELS
    missing = [m['file'] for m in required if not (ROOT / 'Data/Models' / m['folder'] / Path(m['file']).name).exists()]
    if missing:
        raise ValueError('Los modelos de vídeo todavía se están instalando: ' + ', '.join(missing))
    configure_montage(p, data)
    return enqueue_video_batch(request.app, prompt, p, 'Vídeo', data.get('count', 1))


def enqueue_video_batch(app, prompt, params, title, count):
    if type(count) is not int or not 1 <= count <= 5:
        raise ValueError('Elige entre 1 y 5 vídeos por petición.')
    stride = params.get('segment_count', 1)
    seeds = [s * stride for s in random.sample(range(2147483648 // stride), count)] if params['seed'] == -1 else [(params['seed'] + i * stride) % 2147483648 for i in range(count)]
    cid, ids = uuid.uuid4().hex, []
    with DB:
        DB.execute('INSERT INTO chats (id,title,created) VALUES (?,?,?)', (cid, title + ' · ' + prompt[:45], time.time()))
        for index, seed in enumerate(seeds, start=1):
            rid = uuid.uuid4().hex
            p = {**params, 'seed': seed, 'batch_index': index, 'batch_count': count}
            DB.execute('INSERT INTO renders (id,chat_id,prompt,params,status,detail,image,created) VALUES (?,?,?,?,?,?,?,?)',
                (rid, cid, prompt, json.dumps(p), 'queued', f'Vídeo {index} de {count} en cola', None, time.time()))
            ids.append(rid)
    for rid in ids:
        app['queue'].put_nowait(rid)
    return web.json_response({'id': ids[0], 'ids': ids, 'chat': cid, 'count': count})


def configure_montage(params, data):
    duration = data.get('duration_seconds', 0)
    if type(duration) is not int or not 0 <= duration <= 120:
        raise ValueError('La duración total debe ser un número entero entre 1 y 120 segundos, o 0 para un clip.')
    scenes = data.get('scene_prompts', [])
    if not isinstance(scenes, list) or len(scenes) > 64 or any(not isinstance(s, str) or not s.strip() or len(s) > 2000 for s in scenes):
        raise ValueError('El guion admite hasta 64 escenas, de hasta 2000 caracteres cada una.')
    if not duration:
        return
    multiplier = params.get('interpolation', 1)
    fps = params['fps'] * multiplier
    clip_frames = (params['frames'] - 1) * multiplier + 1
    target = duration * fps
    params.update(duration_seconds=duration, output_fps=fps, output_frames=target,
                  segment_count=math.ceil(target / clip_frames), scene_prompts=[s.strip() for s in scenes])


class MontageEncoder:
    def __init__(self, path, params):
        self.params, self.written = params, 0
        self.container = av.open(str(path), mode='w', options={'movflags': '+faststart'})
        self.stream = self.container.add_stream('libx264', rate=Fraction(params['output_fps']))
        self.stream.width, self.stream.height = params['width'], params['height']
        self.stream.pix_fmt = 'yuv420p'
        self.stream.options = {'crf': '18', 'preset': 'fast'}

    def append(self, content):
        added = 0
        with av.open(io.BytesIO(content)) as source:
            if abs(float(source.streams.video[0].average_rate) - self.params['output_fps']) > 0.01:
                raise ValueError('La escena tiene FPS distintos de los solicitados; no se cambia su velocidad.')
            for frame in source.decode(video=0):
                if self.written >= self.params['output_frames']:
                    break
                if (frame.width, frame.height) != (self.params['width'], self.params['height']):
                    raise ValueError('La escena no tiene la resolución solicitada.')
                frame = frame.reformat(format='yuv420p')
                frame.pts = self.written
                frame.time_base = Fraction(1, self.params['output_fps'])
                for packet in self.stream.encode(frame):
                    self.container.mux(packet)
                self.written += 1
                added += 1
        if not added:
            raise ValueError('La escena no contiene fotogramas utilizables.')

    def finish(self):
        if self.written != self.params['output_frames']:
            raise ValueError('No se generaron todos los fotogramas del montaje.')
        for packet in self.stream.encode():
            self.container.mux(packet)
        self.container.close()


async def render_montage(app, row, params):
    project = VIDEO_PROJECTS / row['id']
    project.mkdir(parents=True, exist_ok=True)
    signature = hashlib.sha256(json.dumps([row['prompt'], params], sort_keys=True).encode()).hexdigest()
    manifest = project / 'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text(encoding='utf-8'))['signature'] != signature:
        raise ValueError('Los parámetros no coinciden con las escenas guardadas de este montaje.')
    manifest.write_text(json.dumps({'signature': signature, 'params': params, 'prompt': row['prompt']}, ensure_ascii=False), encoding='utf-8')
    target = project / 'assembled.mp4'
    encoder = MontageEncoder(target, params)
    try:
        for index in range(params['segment_count']):
            prefix = f"Escena {index + 1}/{params['segment_count']} · "
            clip = project / f'{index + 1:03d}.mp4'
            if clip.is_file():
                update(row['id'], detail=prefix + 'Recuperando escena guardada')
                content = await asyncio.to_thread(clip.read_bytes)
            else:
                scene = params['scene_prompts'][index % len(params['scene_prompts'])] if params['scene_prompts'] else ''
                prompt = row['prompt'] + ('\n' + scene if scene else '')
                part = {**params, 'seed': (params['seed'] + index) % 2147483648, 'progress_prefix': prefix}
                update(row['id'], detail=prefix + 'Preparando generación local')
                content = await render_comfy(app, {**dict(row), 'prompt': prompt}, part)
            update(row['id'], detail=prefix + 'Montando vídeo')
            await asyncio.to_thread(encoder.append, content)
            if not clip.is_file():
                temporary = clip.with_suffix('.part')
                await asyncio.to_thread(temporary.write_bytes, content)
                temporary.replace(clip)
        await asyncio.to_thread(encoder.finish)
    except BaseException:
        encoder.container.close()
        raise
    return await asyncio.to_thread(target.read_bytes)


async def resume_montage(request):
    found = rows('SELECT * FROM renders WHERE id=?', (request.match_info['id'],))
    if not found or found[0]['status'] != 'error' or not json.loads(found[0]['params']).get('duration_seconds'):
        raise ValueError('Solo puedes reanudar un montaje que haya terminado con un error.')
    update(found[0]['id'], status='queued', detail='Montaje en cola para reanudar')
    request.app['queue'].put_nowait(found[0]['id'])
    return web.json_response({'id': found[0]['id']})


async def mesh_status(request):
    models = []
    for model in TRELLIS_MODELS:
        target = ROOT / 'Data/Models' / model['folder'] / Path(model['file']).name
        partial = target.with_suffix(target.suffix + '.part')
        models.append({'name': target.name, 'ready': target.exists(), 'downloaded': partial.stat().st_size if partial.exists() else 0})
    return web.json_response({'ready': all(m['ready'] for m in models), 'models': models})


async def generate_mesh(request):
    data = await request.json()
    name = resolve_input(data)
    mode = data.get('mode', 'color')
    steps, seed = int(data.get('steps', 12)), int(data.get('seed', -1))
    faces = int(data.get('faces', 100000))
    if mode not in ('shape', 'color', 'pbr') or not 4 <= steps <= 30 or not 10000 <= faces <= 500000 or not -1 <= seed <= 2147483647:
        raise ValueError('Revisa el modo, los pasos, la semilla y la cantidad de caras del modelo 3D.')
    missing = [m['file'] for m in TRELLIS_MODELS if not (ROOT / 'Data/Models' / m['folder'] / Path(m['file']).name).is_file()]
    if missing:
        raise ValueError('Los modelos de TRELLIS.2 todavía se están instalando: ' + ', '.join(missing))
    title = str(data.get('name', 'Modelo 3D')).strip()[:80] or 'Modelo 3D'
    p = {'kind': 'mesh', 'engine': 'comfy', 'model': 'TRELLIS.2 INT8', 'input_image': name, 'width': 512, 'height': 512,
         'steps': steps, 'seed': random.randrange(2147483648) if seed == -1 else seed, 'mode': mode, 'faces': faces,
         'remove_background': data.get('remove_background', True) is True}
    rid, cid = uuid.uuid4().hex, uuid.uuid4().hex
    with DB:
        DB.execute('INSERT INTO chats (id,title,created) VALUES (?,?,?)', (cid, '3D · ' + title[:45], time.time()))
        DB.execute('INSERT INTO renders (id,chat_id,prompt,params,status,detail,image,created) VALUES (?,?,?,?,?,?,?,?)',
                   (rid, cid, title, json.dumps(p), 'queued', 'Modelo 3D en cola', None, time.time()))
    request.app['queue'].put_nowait(rid)
    return web.json_response({'id': rid, 'chat': cid})


def mesh_workflow(p, image_name):
    def node(kind, **inputs):
        return {'class_type': kind, 'inputs': inputs}
    graph = {
        'image': node('LoadImage', image=image_name),
        'vision': node('CLIPVisionLoader', clip_name=TRELLIS_NAMES['vision']),
        'model': node('UNETLoader', unet_name=TRELLIS_NAMES['model'], weight_dtype='default'),
        'shape_vae': node('VAELoader', vae_name=TRELLIS_NAMES['shape_vae']),
    }
    if p['remove_background']:
        graph['bg_model'] = node('LoadBackgroundRemovalModel', bg_removal_name=TRELLIS_NAMES['background'])
        graph['mask'] = node('RemoveBackground', bg_removal_model=['bg_model', 0], image=['image', 0])
    else:
        graph['mask'] = node('InvertMask', mask=['image', 1])
    graph['crop'] = node('ImageCropToMask', images=['image', 0], masks=['mask', 0], width=1024, height=1024, pad_factor=1.0, grow_mask=0, background='#000000')
    graph['condition'] = node('Trellis2Conditioning', clip_vision_model=['vision', 0], image=['crop', 0])
    graph['structure_cfg'] = node('CFGOverride', model=['model', 0], cfg=1.0, start_percent=0.667, end_percent=1.0)
    graph['structure_rescale'] = node('RescaleCFG', model=['structure_cfg', 0], multiplier=0.7)
    graph['structure_model'] = node('ModelSamplingSD3', model=['structure_rescale', 0], shift=5.0)
    graph['shape_cfg'] = node('CFGOverride', model=['model', 0], cfg=1.0, start_percent=0.769, end_percent=1.0)
    graph['shape_model'] = node('RescaleCFG', model=['shape_cfg', 0], multiplier=0.5)
    graph['empty'] = node('EmptyTrellis2LatentStructure', batch_size=1)
    def sample(model, cond, latent, cfg=7.5):
        return node('KSampler', model=[model, 0], seed=p['seed'], steps=p['steps'], cfg=cfg, sampler_name='euler',
            scheduler='normal', positive=[cond, 0], negative=[cond, 1], latent_image=latent, denoise=1.0)
    graph['structure_sample'] = sample('structure_model', 'condition', ['empty', 0])
    graph['structure_decode'] = node('VaeDecodeStructureTrellis2', samples=['structure_sample', 0], vae=['shape_vae', 0], resolution='32')
    graph['shape_condition'] = node('Trellis2ShapeStage', positive=['condition', 0], negative=['condition', 1], voxel=['structure_decode', 0])
    graph['shape_sample'] = sample('shape_model', 'shape_condition', ['shape_condition', 2])
    graph['shape_decode'] = node('VaeDecodeShapeTrellis', samples=['shape_sample', 0], vae=['shape_vae', 0])
    graph['simplify'] = node('DecimateMesh', mesh=['shape_decode', 0], target_face_count=p['faces'], placement_mode='midpoint')
    graph['smooth'] = node('MeshSmoothNormals', mesh=['simplify', 0], crease_angle=180.0)
    output = ['smooth', 0]
    if p['mode'] != 'shape':
        graph['texture_vae'] = node('VAELoader', vae_name=TRELLIS_NAMES['texture_vae'])
        graph['texture_condition'] = node('Trellis2TextureStage', positive=['condition', 0], negative=['condition', 1], shape_latent=['shape_sample', 0])
        graph['texture_sample'] = sample('model', 'texture_condition', ['texture_condition', 2], cfg=1.0)
        graph['texture_decode'] = node('VaeDecodeTextureTrellis', samples=['texture_sample', 0], vae=['texture_vae', 0], shape_subdivides=['shape_decode', 1])
        if p['mode'] == 'pbr':
            graph['unwrap'] = node('UnwrapMesh', mesh=['smooth', 0], segmenter='pec', resolution=1024, padding=1, weld_distance=0.0002)
            graph['bake'] = node('BakeTextureFromVoxel', mesh=['unwrap', 0], voxel_colors=['texture_decode', 0], texture_size=1024, reference_mesh=['shape_decode', 0])
            graph['material'] = node('ApplyTextureToMesh', mesh=['unwrap', 0], base_color=['bake', 0], metallic=['bake', 1], roughness=['bake', 2])
        else:
            graph['material'] = node('PaintMesh', mesh=['smooth', 0], voxel_colors=['texture_decode', 0])
        output = ['material', 0]
    graph['save'] = node('SaveGLB', mesh=output, filename_prefix='MatrixStudio/trellis2')
    return graph


def sd15_checkpoints():
    found = set()
    for folder in (ROOT / 'Data/Models/StableDiffusion', Path(os.environ.get('MATRIX_STUDIO_COMFY_DIR', str(project_asset('comfy_engine')))) / 'models/checkpoints'):
        if not folder.exists():
            continue
        for file in folder.rglob('*.safetensors'):
            try:
                with file.open('rb') as source:
                    size = struct.unpack('<Q', source.read(8))[0]
                    if size > 16 * 1024 * 1024:
                        continue
                    header = json.loads(source.read(size))
                for key, entry in header.items():
                    if key.endswith('attn2.to_k.weight') and isinstance(entry, dict):
                        shape = entry.get('shape', [])
                        if len(shape) == 2 and shape[1] == 768:
                            found.add(file.relative_to(folder).as_posix())
                        break
            except (OSError, ValueError, struct.error):
                continue
    return sorted(found)


def animatediff_default_checkpoint(checkpoints):
    if ANIMATEDIFF_NAMES['creative_checkpoint'] in checkpoints:
        return ANIMATEDIFF_NAMES['creative_checkpoint']
    if ANIMATEDIFF_NAMES['realistic_checkpoint'] in checkpoints and (ROOT / 'Data/Models/VAE' / ANIMATEDIFF_NAMES['realistic_vae']).is_file():
        return ANIMATEDIFF_NAMES['realistic_checkpoint']
    return ANIMATEDIFF_NAMES['checkpoint']


def animatediff_motion_defaults():
    motion, camera = ANIMATEDIFF_NAMES['motion_v2'], ANIMATEDIFF_NAMES['camera_zoom_out']
    if (ROOT / 'Data/Models/AnimateDiff' / motion).is_file() and (ROOT / 'Data/Models/AnimateDiffMotionLora' / camera).is_file():
        return motion, camera
    return ANIMATEDIFF_NAMES['motion'], ''


async def animatediff_status(request):
    models = []
    for model in ANIMATEDIFF_MODELS:
        target = ROOT / 'Data/Models' / model['folder'] / Path(model['file']).name
        part = target.with_suffix(target.suffix + '.part')
        models.append({'name': target.name, 'ready': target.exists(), 'optional': model.get('optional', False), 'downloaded': part.stat().st_size if part.exists() else 0})
    node_ready = False
    try:
        info = await api(request.app['session'], CONFIG['comfy'] + '/object_info/ADE_AnimateDiffLoaderGen1', timeout=2)
        node_ready = 'ADE_AnimateDiffLoaderGen1' in info
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        pass
    checkpoints = sd15_checkpoints()
    default = animatediff_default_checkpoint(checkpoints)
    installed = {m['name'] for m in models if m['ready']}
    motions = [ANIMATEDIFF_NAMES[k] for k in ('motion', 'motion_v2') if ANIMATEDIFF_NAMES[k] in installed]
    cameras = [ANIMATEDIFF_NAMES[k] for k in ('camera_zoom_out', 'camera_pan_left') if ANIMATEDIFF_NAMES[k] in installed]
    default_motion, default_camera = animatediff_motion_defaults()
    return web.json_response({'ready': bool(checkpoints) and node_ready and all(m['ready'] for m in models if not m['optional']),
        'node_ready': node_ready, 'models': models, 'checkpoints': checkpoints, 'default_checkpoint': default,
        'motion_models': motions, 'motion_loras': cameras, 'default_motion_model': default_motion, 'default_motion_lora': default_camera,
        'interpolation_ready': ANIMATEDIFF_NAMES['interpolation'] in installed})


async def generate_animatediff(request):
    data = await request.json()
    prompt = str(data.get('prompt', '')).strip()
    if not prompt or len(prompt) > 12000:
        raise ValueError('Describe la escena y su movimiento (hasta 12000 caracteres).')
    checkpoints = sd15_checkpoints()
    default = animatediff_default_checkpoint(checkpoints)
    model = str(data.get('model', default))
    if model not in checkpoints:
        raise ValueError('Selecciona un checkpoint SD 1.5 compatible con este módulo de movimiento.')
    vae = ANIMATEDIFF_NAMES['realistic_vae'] if model == ANIMATEDIFF_NAMES['realistic_checkpoint'] else None
    if vae and not (ROOT / 'Data/Models/VAE' / vae).is_file():
        raise ValueError('Instala el VAE MSE recomendado para Realistic Vision antes de generar.')
    motion = ROOT / 'Data/Models/AnimateDiff' / ANIMATEDIFF_NAMES['motion']
    if not motion.is_file():
        raise ValueError('El módulo AnimateDiff v3 todavía no está instalado.')
    default_motion, default_camera = animatediff_motion_defaults()
    motion_model = str(data.get('motion_model', default_motion))
    interpolation = 3 if (ROOT / 'Data/Models/FrameInterpolation' / ANIMATEDIFF_NAMES['interpolation']).is_file() else 1
    p = {'kind': 'video', 'backend': 'animatediff', 'engine': 'comfy', 'model': model, 'vae': vae,
        'motion_model': motion_model,
        'motion_lora': str(data.get('motion_lora', default_camera if motion_model == default_motion else '')), 'motion_lora_strength': float(data.get('motion_lora_strength', 0.3)),
        'motion_scale': float(data.get('motion_scale', 1.15)),
        'free_noise': data.get('free_noise', True),
        'interpolation': data.get('interpolation', interpolation),
        'sampler': str(data.get('sampler', 'dpmpp_2m')), 'scheduler': str(data.get('scheduler', 'karras')),
        'input_image': resolve_input(data) if data.get('input_image') or data.get('render_id') else None,
        'width': int(data.get('width', 512)), 'height': int(data.get('height', 320)), 'frames': int(data.get('frames', 16)),
        'fps': int(data.get('fps', 8)), 'steps': int(data.get('steps', 24)), 'cfg': float(data.get('cfg', 6)),
        'denoise': float(data.get('denoise', 0.65)), 'negative': str(data.get('negative', 'worst quality, low quality, blurry, deformed anatomy, extra limbs, fused bodies, duplicate person, disfigured face, watermark, text')),
        'seed': int(data.get('seed', -1))}
    if any(p[k] < 128 or p[k] > 768 or p[k] % 8 for k in ('width', 'height')) or not 4 <= p['frames'] <= 64 or not 4 <= p['fps'] <= 30:
        raise ValueError('Resolución: múltiplos de 8 entre 128 y 768. Fotogramas: 4–64. FPS: 4–30.')
    if not 4 <= p['steps'] <= 50 or not 1 <= p['cfg'] <= 20 or not 0.05 <= p['denoise'] <= 1 or not -1 <= p['seed'] <= 2147483647:
        raise ValueError('Revisa los pasos, CFG, transformación y semilla.')
    if p['sampler'] not in ('euler', 'dpmpp_2m', 'dpmpp_sde') or p['scheduler'] not in ('normal', 'karras'):
        raise ValueError('Selecciona un muestreador y una planificación compatibles.')
    if type(p['interpolation']) is not int or p['interpolation'] not in (1, 2, 3):
        raise ValueError('Suavidad: original, 2× o 3×.')
    if type(p['free_noise']) is not bool:
        raise ValueError('FreeNoise debe estar activado o desactivado.')
    if p['interpolation'] > 1 and not (ROOT / 'Data/Models/FrameInterpolation' / ANIMATEDIFF_NAMES['interpolation']).is_file():
        raise ValueError('Instala RIFE para activar la suavidad del vídeo.')
    if not 0.5 <= p['motion_scale'] <= 1.5 or not 0 <= p['motion_lora_strength'] <= 1:
        raise ValueError('Movimiento: 0.5–1.5. Intensidad de LoRA: 0–1.')
    if p['motion_model'] not in [ANIMATEDIFF_NAMES[k] for k in ('motion', 'motion_v2')] or not (motion.parent / p['motion_model']).is_file():
        raise ValueError('El módulo temporal seleccionado no está instalado.')
    if p['motion_lora']:
        if p['motion_lora'] not in [ANIMATEDIFF_NAMES[k] for k in ('camera_zoom_out', 'camera_pan_left')] or not (ROOT / 'Data/Models/AnimateDiffMotionLora' / p['motion_lora']).is_file():
            raise ValueError('La LoRA de cámara seleccionada no está instalada.')
        if p['motion_model'] != ANIMATEDIFF_NAMES['motion_v2']:
            raise ValueError('Las LoRA de cámara disponibles requieren AnimateDiff v2.')
    if not p['input_image']:
        p['denoise'] = 1.0
    configure_montage(p, data)
    return enqueue_video_batch(request.app, prompt, p, 'AnimateDiff', data.get('count', 1))


def animatediff_workflow(p, prompt, image_name=None):
    def node(kind, **inputs):
        return {'class_type': kind, 'inputs': inputs}
    graph = {
        'checkpoint': node('CheckpointLoaderSimple', ckpt_name=p['model']),
        'positive': node('CLIPTextEncode', text=prompt, clip=['checkpoint', 1]),
        'negative': node('CLIPTextEncode', text=p['negative'], clip=['checkpoint', 1]),
        'context': node('ADE_StandardUniformContextOptions', context_length=16, context_stride=1, context_overlap=4, fuse_method='pyramid'),
        'motion': node('ADE_AnimateDiffLoaderGen1', model=['checkpoint', 0], model_name=p.get('motion_model', ANIMATEDIFF_NAMES['motion']),
            beta_schedule='autoselect', context_options=['context', 0]),
    }
    graph['motion_scale'] = node('ADE_MultivalDynamic', float_val=p.get('motion_scale', 1.0))
    graph['motion']['inputs']['scale_multival'] = ['motion_scale', 0]
    if p['frames'] > 16 and p.get('free_noise', True):
        graph['context']['inputs']['context_overlap'] = 8
        graph['noise'] = node('ADE_AnimateDiffSamplingSettings', batch_offset=0, noise_type='FreeNoise', seed_gen='comfy', seed_offset=0)
        graph['motion']['inputs']['sample_settings'] = ['noise', 0]
    if p.get('motion_lora'):
        graph['camera_lora'] = node('ADE_AnimateDiffLoRALoader', name=p['motion_lora'], strength=p['motion_lora_strength'])
        graph['motion']['inputs']['motion_lora'] = ['camera_lora', 0]
    vae = ['checkpoint', 2]
    if p.get('vae'):
        graph['vae'] = node('VAELoader', vae_name=p['vae'])
        vae = ['vae', 0]
    if image_name:
        graph['reference'] = node('LoadImage', image=image_name)
        graph['resize'] = node('ImageScale', image=['reference', 0], upscale_method='lanczos', width=p['width'], height=p['height'], crop='center')
        graph['encode'] = node('VAEEncode', pixels=['resize', 0], vae=vae)
        graph['latent'] = node('RepeatLatentBatch', samples=['encode', 0], amount=p['frames'])
    else:
        graph['latent'] = node('EmptyLatentImage', width=p['width'], height=p['height'], batch_size=p['frames'])
    graph['sample'] = node('KSampler', model=['motion', 0], positive=['positive', 0], negative=['negative', 0],
        latent_image=['latent', 0], seed=p['seed'], steps=p['steps'], cfg=p['cfg'], sampler_name=p.get('sampler', 'euler'), scheduler=p.get('scheduler', 'normal'), denoise=p['denoise'])
    graph['decode'] = node('VAEDecodeTiled', samples=['sample', 0], vae=vae, tile_size=256, overlap=64, temporal_size=16, temporal_overlap=4)
    images, multiplier = ['decode', 0], p.get('interpolation', 1)
    if multiplier > 1:
        graph['interpolation_model'] = node('FrameInterpolationModelLoader', model_name=ANIMATEDIFF_NAMES['interpolation'])
        graph['interpolate'] = node('FrameInterpolate', interp_model=['interpolation_model', 0], images=images, multiplier=multiplier)
        images = ['interpolate', 0]
    graph['video'] = node('CreateVideo', images=images, fps=p['fps'] * multiplier)
    graph['save'] = node('SaveVideo', video=['video', 0], filename_prefix='MatrixStudio/animatediff', format='mp4', **{'format.codec': 'h264'})
    return graph


def video_workflow(p, prompt, image_name):
    def node(kind, **inputs):
        return {'class_type': kind, 'inputs': inputs}
    if p.get('family') == 'wan5b':
        return {
            'image': node('LoadImage', image=image_name),
            'text': node('CLIPLoaderGGUF', clip_name=WAN_NAMES['text'], type='wan'),
            'positive': node('CLIPTextEncode', text=prompt, clip=['text', 0]),
            'negative': node('CLIPTextEncode', text=p['negative'], clip=['text', 0]),
            'vae': node('VAELoader', vae_name=WAN5B_NAMES['vae']),
            'model': node('UnetLoaderGGUF', unet_name=WAN5B_NAMES['model']),
            'shift': node('ModelSamplingSD3', model=['model', 0], shift=p['shift']),
            'latent': node('Wan22ImageToVideoLatent', vae=['vae', 0], width=p['width'], height=p['height'],
                           length=p['frames'], batch_size=1, start_image=['image', 0]),
            'sample': node('KSampler', model=['shift', 0], positive=['positive', 0], negative=['negative', 0],
                           latent_image=['latent', 0], seed=p['seed'], steps=p['steps'], cfg=p['cfg'],
                           sampler_name='uni_pc', scheduler='simple', denoise=1.0),
            'decode': node('VAEDecodeTiled', samples=['sample', 0], vae=['vae', 0], tile_size=256, overlap=64, temporal_size=16, temporal_overlap=4),
            'video': node('CreateVideo', images=['decode', 0], fps=p['fps']),
            'save': node('SaveVideo', video=['video', 0], filename_prefix='MatrixStudio/wan5b', format='mp4', **{'format.codec': 'h264'}),
        }
    graph = {
        'image': node('LoadImage', image=image_name),
        'text': node('CLIPLoaderGGUF', clip_name=WAN_NAMES['text'], type='wan'),
        'positive': node('CLIPTextEncode', text=prompt, clip=['text', 0]),
        'negative': node('CLIPTextEncode', text=p['negative'], clip=['text', 0]),
        'vae': node('VAELoader', vae_name=WAN_NAMES['vae']),
        'conditioning': node('WanImageToVideo', positive=['positive', 0], negative=['negative', 0],
            vae=['vae', 0], width=p['width'], height=p['height'], length=p['frames'], batch_size=1, start_image=['image', 0]),
    }
    for phase in ('high', 'low'):
        graph[phase] = node('UnetLoaderGGUF', unet_name=WAN_NAMES[phase])
        model = [phase, 0]
        if p.get('profile', 'fast') == 'fast':
            graph[phase + '_lora'] = node('LoraLoaderModelOnly', model=model, lora_name=WAN_NAMES['lora_' + phase], strength_model=1.0)
            model = [phase + '_lora', 0]
        graph[phase + '_shift'] = node('ModelSamplingSD3', model=model, shift=p.get('shift', 5.0))
    steps, shift = p.get('steps', 4), p.get('shift', 5.0)
    split = min(steps - 1, max(1, math.ceil(round(steps * (1 - 0.9 / (shift - (shift - 1) * 0.9)), 10))))
    for phase, start, end in (('high', 0, split), ('low', split, steps)):
        graph[phase + '_sample'] = node('KSamplerAdvanced', model=[phase + '_shift', 0],
            add_noise='enable' if phase == 'high' else 'disable', noise_seed=p['seed'], steps=steps, cfg=p.get('cfg', 1.0),
            sampler_name='euler' if p.get('profile', 'fast') == 'fast' else 'uni_pc', scheduler='simple', positive=['conditioning', 0], negative=['conditioning', 1],
            latent_image=['conditioning', 2] if phase == 'high' else ['high_sample', 0], start_at_step=start,
            end_at_step=end, return_with_leftover_noise='enable' if phase == 'high' else 'disable')
    graph['decode'] = node('VAEDecodeTiled', samples=['low_sample', 0], vae=['vae', 0], tile_size=256, overlap=64, temporal_size=16, temporal_overlap=4)
    graph['video'] = node('CreateVideo', images=['decode', 0], fps=p['fps'])
    graph['save'] = node('SaveVideo', video=['video', 0], filename_prefix='MatrixStudio/video', format='mp4', **{'format.codec': 'h264'})
    return graph


async def render_comfy(app, row, p):
    session, url = app['session'], CONFIG['comfy']
    cid = uuid.uuid4().hex
    is_video = p.get('kind') == 'video'
    is_mesh = p.get('kind') == 'mesh'
    is_animatediff = p.get('backend') == 'animatediff'
    def progress(**values):
        update(row['id'], detail=p.get('progress_prefix', '') + values['detail'])
    if is_video or is_mesh:
        image_name = None
        if p.get('input_image'):
            form = aiohttp.FormData()
            form.add_field('image', (INPUTS / p['input_image']).read_bytes(), filename=p['input_image'], content_type='image/png')
            async with session.post(url + '/upload/image', data=form, allow_redirects=False) as response:
                response.raise_for_status()
                uploaded = await response.json()
            image_name = '/'.join(filter(None, (uploaded.get('subfolder'), uploaded['name'])))
        graph = animatediff_workflow(p, row['prompt'], image_name) if is_animatediff else mesh_workflow(p, image_name) if is_mesh else video_workflow(p, row['prompt'], image_name)
    else:
        graph = workflow(p, row['prompt'])
    async with session.ws_connect(url + '/ws?clientId=' + cid, timeout=10) as ws:
        result = await api(session, url + '/prompt', {'prompt': graph, 'client_id': cid})
        pid = result['prompt_id']
        current_node = None
        async with asyncio.timeout(7200 if is_video or is_mesh else 3600):
            async for msg in ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break
                    continue
                event = json.loads(msg.data)
                data = event.get('data', {})
                if data.get('prompt_id') != pid:
                    continue
                kind = event['type']
                if kind == 'executing':
                    current_node = data.get('node')
                if is_animatediff and kind == 'executing' and data.get('node'):
                    stage = {'checkpoint': 'Cargando SD 1.5', 'motion': 'Aplicando AnimateDiff', 'camera_lora': 'Aplicando LoRA de cámara',
                             'sample': 'Generando movimiento temporal', 'decode': 'Decodificando fotogramas',
                             'interpolate': 'Suavizando el movimiento con RIFE', 'save': 'Guardando MP4'}
                    progress(detail=stage.get(data['node'], 'Preparando AnimateDiff local…'))
                if is_video and not is_animatediff and kind == 'executing' and data.get('node'):
                    stage = {'text': 'Cargando codificador de texto', 'positive': 'Interpretando el movimiento', 'model': 'Cargando Wan 5B', 'sample': 'Generando escena',
                             'high': 'Cargando modelo de movimiento', 'high_sample': 'Generando movimiento · fase 1 de 2',
                             'low': 'Cargando modelo de detalle', 'low_sample': 'Generando detalle · fase 2 de 2',
                             'decode': 'Decodificando fotogramas', 'save': 'Guardando MP4'}
                    progress(detail=stage.get(data['node'], 'Preparando vídeo local…'))
                if is_mesh and kind == 'executing' and data.get('node'):
                    stage = {'mask': 'Separando el objeto del fondo', 'condition': 'Analizando la imagen',
                             'model': 'Cargando TRELLIS.2 INT8', 'structure_sample': 'Generando estructura 3D',
                             'shape_sample': 'Refinando la geometría', 'shape_decode': 'Reconstruyendo la malla',
                             'texture_sample': 'Generando materiales', 'simplify': 'Simplificando la malla',
                             'unwrap': 'Preparando coordenadas UV', 'bake': 'Creando texturas PBR', 'save': 'Guardando GLB'}
                    progress(detail=stage.get(data['node'], 'Preparando modelo 3D local…'))
                if kind == 'progress':
                    if is_video and current_node in ('decode', 'interpolate'):
                        label = 'Decodificando fotogramas' if current_node == 'decode' else 'Suavizando movimiento'
                        progress(detail=f"{label} · {round(100 * data['value'] / max(1, data['max']))}%")
                    else:
                        progress(detail=f"Paso {data['value']} de {data['max']}")
                if kind in ('execution_error', 'execution_interrupted'):
                    raise ValueError(data.get('exception_message', 'Generación interrumpida en ComfyUI.'))
                if kind == 'execution_success' or (kind == 'executing' and data.get('node') is None):
                    break
        for attempt in range(20):
            history = await api(session, url + '/history/' + pid)
            if pid in history:
                break
            await asyncio.sleep(0.25)
        for output in history.get(pid, {}).get('outputs', {}).values():
            for img in output.get('images', []) + output.get('3d', []):
                expected = '.glb' if is_mesh else '.mp4' if is_video else '.png'
                if Path(img.get('filename', '')).suffix.lower() != expected:
                    continue
                image_query = {key: img[key] for key in ('filename', 'subfolder', 'type') if key in img}
                async with session.get(url + '/view', params=image_query, allow_redirects=False) as response:
                    response.raise_for_status()
                    return await response.read()
        raise ValueError('ComfyUI no devolvió el archivo generado. Revisa el modelo y su workflow.')


async def render_qwen(app, row, p):
    if not all(path.exists() for path in QFILES):
        raise ValueError('Qwen necesita estos archivos: ' + ', '.join(str(path) for path in QFILES if not path.exists()))
    env = {**os.environ, 'PATH': str(CUDA) + os.pathsep + os.environ['PATH']}
    target = OUTPUT / (row['id'] + '.png')
    args = [str(QFILES[0]), '--diffusion-model', str(QFILES[1]), '--llm', str(QFILES[2]), '--vae', str(QFILES[3]),
        '--prompt', row['prompt'], '--negative-prompt', p['negative'], '--steps', str(p['steps']), '--cfg-scale', str(p['cfg']),
        '--sampling-method', 'euler', '--width', str(p['width']), '--height', str(p['height']), '--seed', str(p['seed']),
        '--backend', 'cuda0', '--max-vram', '6', '--mmap', '--flash-attn', 'on', '--vae-tiling', '--output', str(target)]
    if p['steps'] == 8:
        args += ['--sigmas', '1.0,0.978453,0.95418,0.926626,0.89508,0.845148,0.704534,0.414568,0.0']
    with open(OUTPUT / (row['id'] + '.log'), 'w', encoding='utf-8') as log:
        proc = await asyncio.create_subprocess_exec(*args, env=env, cwd=QWEN, stdout=log, stderr=log)
        app['qwen_process'] = proc
        try:
            async with asyncio.timeout(3600):
                code = await proc.wait()
        finally:
            if proc.returncode is None:
                proc.terminate()
                await proc.wait()
            app['qwen_process'] = None
    if code or not target.exists():
        raise ValueError(f'Qwen terminó con código {code}. Consulta outputs/{row["id"]}.log')
    return target.read_bytes()


async def worker(app):
    while True:
        rid = await app['queue'].get()
        row = rows('SELECT * FROM renders WHERE id=?', (rid,))[0]
        p = json.loads(row['params'])
        update(rid, status='running', detail='Cargando modelo y generando…')
        try:
            if p['engine'] == 'comfy':
                content = await render_montage(app, row, p) if p.get('duration_seconds') else await render_comfy(app, row, p)
            elif p['engine'] == 'qwen':
                content = await render_qwen(app, row, p)
            else:
                payload = {k: p[k] for k in ('width', 'height', 'steps', 'seed')}
                payload.update(prompt=row['prompt'], negative_prompt=p['negative'], cfg_scale=p['cfg'], batch_size=1)
                if p['model']:
                    payload['override_settings'] = {'sd_model_checkpoint': p['model']}
                result = await api(app['session'], CONFIG['automatic'] + '/sdapi/v1/txt2img', payload, timeout=3600)
                content = base64.b64decode(result['images'][0].split(',')[-1])
            filename = rid + {'video': '.mp4', 'mesh': '.glb'}.get(p.get('kind'), '.png')
            (OUTPUT / filename).write_bytes(content)
            update(rid, status='done', image='/outputs/' + filename, detail={'video': 'Vídeo listo', 'mesh': 'Modelo 3D listo'}.get(p.get('kind'), 'Imagen lista'))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            update(rid, status='error', detail=str(exc) or 'No se pudo conectar con el motor. Inícialo desde Motores.')
        finally:
            app['queue'].task_done()


async def lifecycle(app):
    DB.execute("UPDATE renders SET status='error', detail='El servidor se reinició. Puedes volver a generar.' WHERE status IN ('queued','running')")
    DB.commit()
    app['session'] = aiohttp.ClientSession()
    app['queue'] = asyncio.Queue()
    task = asyncio.create_task(worker(app))
    yield
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    await app['session'].close()
    proc = app.get('comfy_process')
    if proc and proc.returncode is None:
        proc.terminate()
        await proc.wait()
    DB.close()


async def index(request):
    return web.FileResponse(APP / 'index.html')


def create_app():
    app = web.Application(middlewares=[boundary], client_max_size=21 * 1024 * 1024)
    app.cleanup_ctx.append(lifecycle)
    app.router.add_get('/', index)
    app.router.add_get('/api/engines', engines)
    app.router.add_post('/api/settings', settings)
    app.router.add_post('/api/engines/comfy/start', boot_comfy)
    app.router.add_get('/api/chats', chats)
    app.router.add_get('/api/renders', renders)
    app.router.add_post('/api/renders/{id:[a-f0-9]{32}}/resume', resume_montage)
    app.router.add_post('/api/generate', generate)
    app.router.add_get('/api/video/status', video_status)
    app.router.add_post('/api/video/input', video_input)
    app.router.add_post('/api/video/generate', generate_video)
    app.router.add_get('/api/3d/status', mesh_status)
    app.router.add_post('/api/3d/input', video_input)
    app.router.add_post('/api/3d/generate', generate_mesh)
    app.router.add_get('/api/animatediff/status', animatediff_status)
    app.router.add_post('/api/animatediff/input', video_input)
    app.router.add_post('/api/animatediff/generate', generate_animatediff)
    app.router.add_post('/api/{kind:chats|renders}/{id:[a-f0-9]{32}}/{action:delete|restore}', delete_item)
    app.router.add_static('/assets/', APP / 'assets')
    app.router.add_static('/outputs/', OUTPUT)
    app.router.add_static('/inputs/', INPUTS)
    return app


def main():
    from urllib.request import urlopen
    try:
        with urlopen(f'http://127.0.0.1:{PORT}/', timeout=1) as response:
            already_running = b'Matrix Studio' in response.read(2048)
    except OSError:
        already_running = False
    if already_running:
        print(f'Matrix Studio ya está abierto: http://127.0.0.1:{PORT}', flush=True)
        if '--no-browser' not in sys.argv:
            webbrowser.open(f'http://127.0.0.1:{PORT}')
        DB.close()
        return
    app = create_app()
    print(f'Matrix Studio · http://127.0.0.1:{PORT}', flush=True)
    if '--no-browser' not in sys.argv:
        import threading
        threading.Timer(1.5, lambda: webbrowser.open(f'http://127.0.0.1:{PORT}')).start()
    web.run_app(app, host='127.0.0.1', port=PORT, print=None)


if __name__ == '__main__':
    main()

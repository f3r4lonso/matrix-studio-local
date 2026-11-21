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
from action_editing import join_action_segments
from image_batches import normalize_batch, store_batch, batch_summaries
from gpu_memory import release_idle_backends
from image_customization import discover_options, validate_selection, image_workflow
from action_profiles import prepare_action, validate_adapters, required_adapters, preset_status, NAMES as ACTION_NAMES
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
CREATE TABLE IF NOT EXISTS image_batches (id TEXT PRIMARY KEY, chat_id TEXT NOT NULL, name TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS studio_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
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


class GenerationStopped(Exception):
    """A user-requested stop, distinct from a generation failure."""



def queue_render(app, rid):
    if rid not in app['queued_ids'] and app.get('active_id') != rid:
        found = rows('SELECT rowid AS position FROM renders WHERE id=?', (rid,))
        if found:
            app['queued_ids'].add(rid)
            app['queue'].put_nowait((found[0]['position'], rid))



def pause_generation_queue(app):
    app['queue_gate'].clear()
    DB.execute("INSERT OR REPLACE INTO studio_settings (key,value) VALUES ('queue_paused','1')")
    DB.commit()



def generation_queue_state(app):
    counts = {r['status']: r['n'] for r in rows('SELECT status,count(*) AS n FROM renders GROUP BY status')}
    failed = sum(bool(json.loads(row['params']).get('image_batch_id')) for row in rows("SELECT params FROM renders WHERE status='error'"))
    return {'paused': not app['queue_gate'].is_set(), 'stopping': app.get('stopping', False),
            'active_id': app.get('active_id'), 'queued': counts.get('queued', 0),
            'paused_jobs': counts.get('paused', 0), 'failed_jobs': failed, 'error': app.get('queue_error', ''), 'gpu': gpu_state(app)}



def gpu_state(app):
    return {'enabled':app.get('release_gpu_enabled', True), 'cleaning':app.get('gpu_cleaning', False),
            'last_report':app.get('gpu_last_report'), 'warning':app.get('gpu_warning', '')}


async def clean_gpu_memory(app, force=False):
    if not force and not app.get('release_gpu_enabled', True):
        return
    async with app['gpu_cleanup_lock']:
        app['gpu_cleaning'] = True
        try:
            report = await release_idle_backends(app['session'], CONFIG)
            app['gpu_last_report'] = report
            app['gpu_warning'] = ' '.join(e['detail'] for e in report['engines'] if e['status'] in ('error','busy','requested'))
        except Exception as exc:
            # Cleanup failure must never turn a completed image into a failed job.
            app['gpu_warning'] = 'No se pudo confirmar la limpieza GPU: ' + str(exc)
        finally:
            app['gpu_cleaning'] = False


async def gpu_settings(request):
    data = await request.json()
    if not isinstance(data, dict) or type(data.get('enabled')) is not bool:
        raise ValueError('enabled debe ser true o false.')
    app = request.app
    app['release_gpu_enabled'] = data['enabled']
    DB.execute("INSERT OR REPLACE INTO studio_settings (key,value) VALUES ('release_gpu_after_job',?)", ('1' if data['enabled'] else '0',))
    DB.commit()
    return web.json_response(gpu_state(app))


async def gpu_release(request):
    app = request.app
    if app.get('active_id') or app.get('gpu_cleaning'):
        raise ValueError('Espera a que termine la generación o limpieza activa.')
    await clean_gpu_memory(app, force=True)
    return web.json_response(gpu_state(app))


async def render_with_clean_memory(app, row, p):
    await clean_gpu_memory(app)
    if app.get('stop_requested') == row['id']:
        raise GenerationStopped()
    update(row['id'], detail='Cargando modelo y generando…')
    if p['engine'] == 'comfy':
        return await (render_montage(app, row, p) if p.get('duration_seconds') else render_comfy(app, row, p))
    if p['engine'] == 'qwen':
        return await render_qwen(app, row, p)
    return await render_automatic(app, row, p)


async def queue_status(request):
    return web.json_response(generation_queue_state(request.app))



async def queue_pause(request):
    pause_generation_queue(request.app)
    request.app['queue_error'] = ''
    return web.json_response(generation_queue_state(request.app))



async def backend_command(app, url, payload):
    async with app['session'].post(url, json=payload, allow_redirects=False,
                                  timeout=aiohttp.ClientTimeout(total=15)) as response:
        if response.status != 200:
            raise ValueError(f'El motor rechazó detener la tarea: HTTP {response.status}')
        await response.read()



async def stop_owned_comfy(app, execution):
    url = execution['url']
    pid, client = execution.get('prompt_id'), execution['client_id']
    for attempt in range(240):
        queue = await api(app['session'], url + '/queue')
        def owned(item):
            return item[1] == pid if pid else item[3].get('client_id') == client
        pending = [item[1] for item in queue['queue_pending'] if owned(item)]
        running = [item[1] for item in queue['queue_running'] if owned(item)]
        if pending:
            await backend_command(app, url + '/queue', {'delete': pending})
        if running and attempt == 0:
            # Recent ComfyUI verifies this ID again inside its interrupt endpoint.
            await backend_command(app, url + '/interrupt', {'prompt_id': running[0]})
        if not pending and not running:
            return
        # A formerly pending task may have started between inspection and removal.
        if running and attempt > 0:
            await backend_command(app, url + '/interrupt', {'prompt_id': running[0]})
        await asyncio.sleep(0.25)
    raise ValueError('ComfyUI todavía no ha confirmado la detención; la cola permanece pausada.')



async def stop_owned_automatic(app, execution):
    # A1111/Forge's public interrupt is global: first verify our force_task_id.
    # Engines without task-level progress are allowed to finish; never guess ownership.
    interrupted = False
    for attempt in range(240):
        request_task = execution.get('request_task')
        if request_task is not None and request_task.done():
            return
        state = await api(app['session'], execution['url'] + '/internal/progress',
                          {'id_task': execution['task_id'], 'live_preview': False})
        if state.get('completed'):
            return
        if state.get('active') and not interrupted:
            await backend_command(app, execution['url'] + '/sdapi/v1/interrupt', {})
            interrupted = True
        if not state.get('active') and not state.get('queued') and attempt > 40 and not interrupted:
            raise ValueError('El motor no permite identificar esta tarea para detenerla de forma selectiva. La cola está pausada.')
        await asyncio.sleep(0.25)
    raise ValueError('Forge todavía no ha confirmado la detención; la cola permanece pausada.')



async def stop_active_generation(app):
    task = app.get('render_task')
    rid = app.get('active_id')
    try:
        async with app['backend_submission_lock']:
            execution = app.get('execution')
            if execution and execution['engine'] == 'comfy':
                await stop_owned_comfy(app, execution)
            elif execution and execution['engine'] == 'automatic':
                await stop_owned_automatic(app, execution)
        if task and not task.done():
            task.cancel()
        if task:
            await asyncio.gather(task, return_exceptions=True)
            while app.get('active_id') == rid and app.get('render_task') is task:
                await asyncio.sleep(0)
    except Exception as exc:
        app['queue_error'] = str(exc)
        app['stop_requested'] = None
    finally:
        app['stopping'] = False



async def run_thread_safely(function, *args):
    task = asyncio.create_task(asyncio.to_thread(function, *args))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        await task
        raise



async def queue_resume(request):
    app = request.app
    if app.get('stopping'):
        raise ValueError('Espera a que el motor confirme la detención antes de continuar.')
    for row in rows("SELECT id,params,status FROM renders WHERE status IN ('paused','error') ORDER BY rowid"):
        if row['status'] == 'error' and not json.loads(row['params']).get('image_batch_id'):
            continue
        update(row['id'], status='queued', detail='En cola para continuar con la misma semilla')
        queue_render(app, row['id'])
    # Recover any pending rows not present in this worker's in-memory heap.
    for pending in rows("SELECT id FROM renders WHERE status='queued' ORDER BY rowid"):
        queue_render(app, pending['id'])
    DB.execute("INSERT OR REPLACE INTO studio_settings (key,value) VALUES ('queue_paused','0')")
    DB.commit()
    app['stop_requested'] = None
    app['queue_error'] = ''
    app['stop_requested'] = None
    app['queue_error'] = ''
    app['queue_gate'].set()
    return web.json_response(generation_queue_state(app))



async def queue_stop(request):
    app = request.app
    pause_generation_queue(app)
    if app.get('active_id') and not app.get('stopping'):
        app['stop_requested'] = app['active_id']
        app['stopping'] = True
        app['queue_error'] = ''
        update(app['active_id'], detail='Deteniendo la generación; se conservará la cola…')
        app['stop_control_task'] = asyncio.create_task(stop_active_generation(app))
    return web.json_response(generation_queue_state(app))



async def render_automatic(app, row, p):
    payload = {k: p[k] for k in ('width', 'height', 'steps', 'seed')}
    payload.update(prompt=row['prompt'], negative_prompt=p['negative'], cfg_scale=p['cfg'], batch_size=1,
                   force_task_id='task(matrix-' + row['id'] + ')')
    payload['override_settings'] = {'sd_model_checkpoint': p['model']} if p['model'] else {}
    if p.get('sampler'):payload['sampler_name'] = p['sampler']
    if p.get('scheduler'):payload['scheduler'] = p['scheduler']
    if p.get('loras'):
        payload['prompt'] += ' ' + ' '.join(f"<lora:{item['name']}:{item['strength_model']}>" for item in p['loras'])
    if p.get('image_batch_id') or p.get('vae'):
        options = await available_image_options(app, 'automatic')
        if not p.get('vae'):
            payload['override_settings']['forge_additional_modules' if options['driver']=='forge' else 'sd_vae'] = [] if options['driver']=='forge' else 'Automatic'
    if p.get('vae'):
        if options['driver'] == 'forge':
            modules = await api(app['session'], CONFIG['automatic']+'/sdapi/v1/sd-modules')
            selected = next((item for item in modules if item['model_name']==p['vae']),None)
            if selected is None:raise ValueError('El VAE seleccionado ya no está disponible.')
            payload['override_settings']['forge_additional_modules'] = [selected['filename']]
        else:
            payload['override_settings']['sd_vae'] = p['vae']
    payload['override_settings_restore_afterwards'] = True
    endpoint = '/sdapi/v1/txt2img'
    if p.get('input_image'):
        payload['init_images'] = [base64.b64encode((INPUTS/p['input_image']).read_bytes()).decode()]
        payload['denoising_strength'] = p.get('denoise',.65)
        payload['resize_mode'] = 1
        endpoint = '/sdapi/v1/img2img'
    execution = {'engine': 'automatic', 'url': CONFIG['automatic'], 'task_id': payload['force_task_id']}
    app['execution'] = execution
    if app.get('stop_requested') == row['id']:
        raise GenerationStopped()
    execution['request_task'] = asyncio.create_task(api(app['session'], execution['url'] + endpoint, payload, timeout=3600))
    result = await execution['request_task']
    return base64.b64decode(result['images'][0].split(',')[-1])


async def worker(app):
    while True:
        await app['queue_gate'].wait()
        _, rid = await app['queue'].get()
        try:
            await app['queue_gate'].wait()
            app['queued_ids'].discard(rid)
            found = rows('SELECT * FROM renders WHERE id=?', (rid,))
            if not found or found[0]['status'] != 'queued':
                continue
            row = found[0]
            p = json.loads(row['params'])
            app['active_id'] = rid
            app['execution'] = None
            update(rid, status='running', detail='Preparando memoria GPU…')
            app['render_task'] = asyncio.create_task(render_with_clean_memory(app, row, p))
            content = await app['render_task']
            if app.get('stop_requested') == rid:
                raise GenerationStopped()
            filename = rid + {'video': '.mp4', 'mesh': '.glb'}.get(p.get('kind'), '.png')
            (OUTPUT / filename).write_bytes(content)
            update(rid, status='done', image='/outputs/' + filename, detail={'video': 'Vídeo listo', 'mesh': 'Modelo 3D listo'}.get(p.get('kind'), 'Imagen lista'))
        except asyncio.CancelledError:
            if app.get('active_id') == rid:
                update(rid, status='paused', detail='Generación detenida. Continuar vuelve a intentar el elemento o escena con la misma semilla.')
            if asyncio.current_task().cancelling():
                raise
        except Exception as exc:
            if isinstance(exc, GenerationStopped) or app.get('stop_requested') == rid:
                update(rid, status='paused', detail='Generación detenida. Los resultados terminados se conservan; pulsa Continuar.')
            else:
                update(rid, status='error', detail=str(exc) or 'No se pudo conectar con el motor. Inícialo desde Motores.')
                if p.get('image_batch_id'):
                    pause_generation_queue(app)
                    app['queue_error'] = 'El lote se ha detenido en una imagen con error. Corrige la causa y pulsa Continuar para reintentar sin saltarla.'
        finally:
            if app.get('active_id') == rid:
                await clean_gpu_memory(app)
            app['queued_ids'].discard(rid)
            app['active_id'] = None
            app['execution'] = None
            app['render_task'] = None
            app['queue'].task_done()


async def lifecycle(app):
    recovered = rows("SELECT id FROM renders WHERE status='running'")
    DB.execute("UPDATE renders SET status='paused', detail='Generación interrumpida al cerrar el servidor. Pulsa Continuar para volver a intentarla.' WHERE status='running'")
    if recovered:
        DB.execute("INSERT OR REPLACE INTO studio_settings (key,value) VALUES ('queue_paused','1')")
    DB.commit()
    app['session'] = aiohttp.ClientSession()
    app['gpu_cleanup_lock'] = asyncio.Lock()
    memory_policy = rows("SELECT value FROM studio_settings WHERE key='release_gpu_after_job'")
    app['release_gpu_enabled'] = not memory_policy or memory_policy[0]['value'] != '0'
    app['gpu_cleaning'] = False
    app['gpu_last_report'] = None
    app['gpu_warning'] = ''
    app['queue'] = asyncio.PriorityQueue()
    app['queued_ids'] = set()
    app['queue_gate'] = asyncio.Event()
    app['backend_submission_lock'] = asyncio.Lock()
    app['active_id'] = None
    app['render_task'] = None
    app['execution'] = None
    app['stopping'] = False
    app['stop_requested'] = None
    app['queue_error'] = ''
    paused = rows("SELECT value FROM studio_settings WHERE key='queue_paused'")
    if not paused or paused[0]['value'] != '1':
        app['queue_gate'].set()
    for row in rows("SELECT id FROM renders WHERE status='queued' ORDER BY created,id"):
        queue_render(app, row['id'])
    task = asyncio.create_task(worker(app))
    yield
    if app.get('active_id') or app['queued_ids']:
        pause_generation_queue(app)
    if app.get('active_id'):
        app['stop_requested'] = app['active_id']
        stop = app.get('stop_control_task')
        if stop and not stop.done():
            await stop
        else:
            await stop_active_generation(app)
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
    app.router.add_post('/api/gpu/settings', gpu_settings)
    app.router.add_post('/api/gpu/release', gpu_release)
    app.router.add_get('/api/image-options', image_options)
    app.router.add_post('/api/image/input', video_input)
    app.router.add_post('/api/image-batches/{id}/settings', change_batch_settings)
    app.router.add_get('/api/image-batches', list_image_batches)
    app.router.add_post('/api/image-batches', import_image_batch)
    app.router.add_get('/api/queue/status', queue_status)
    app.router.add_post('/api/queue/pause', queue_pause)
    app.router.add_post('/api/queue/resume', queue_resume)
    app.router.add_post('/api/queue/stop', queue_stop)
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
    app.router.add_post('/api/video/continue', continue_action)
    app.router.add_post('/api/video/assemble', assemble_action)
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

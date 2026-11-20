"""Ask idle backends to unload models; never reset the GPU or terminate processes."""
import asyncio
import time
import aiohttp


async def request(session, url, payload=None):
    async with session.request('GET' if payload is None else 'POST', url, json=payload,
                               allow_redirects=False, timeout=aiohttp.ClientTimeout(total=5)) as response:
        if response.status != 200:
            raise ValueError(f'HTTP {response.status}')
        if payload is not None:
            await response.read()
            return None
        return await response.json()


async def release_comfy(session, url):
    queue = await request(session, url + '/queue')
    if queue['queue_running'] or queue['queue_pending']:
        return {'engine':'comfy', 'status':'busy', 'detail':'ComfyUI ocupado: no se descargan sus modelos.'}
    await request(session, url + '/free', {'unload_models':True, 'free_memory':True})
    # /free sets flags on the worker thread; HTTP 200 alone does not prove completion.
    for attempt in range(20):
        stats = await request(session, url + '/system_stats')
        devices = [d for d in stats['devices'] if d.get('type') == 'cuda']
        if devices and all(d['torch_vram_total'] <= 256 * 1024**2 for d in devices):
            return {'engine':'comfy', 'status':'released', 'detail':'Caché GPU de ComfyUI liberada.'}
        if not devices:
            return {'engine':'comfy', 'status':'requested', 'detail':'Descarga solicitada a ComfyUI; sin medición CUDA disponible.'}
        queue = await request(session, url + '/queue')
        if queue['queue_running'] or queue['queue_pending']:
            return {'engine':'comfy', 'status':'busy', 'detail':'ComfyUI tiene otro trabajo: se deja continuar.'}
        await asyncio.sleep(.25)
    return {'engine':'comfy', 'status':'requested', 'detail':'Descarga solicitada a ComfyUI; todavía no se confirma la liberación.'}


async def release_automatic(session, url):
    progress = await request(session, url + '/sdapi/v1/progress?skip_current_image=true')
    state = progress['state']
    if state.get('job_count') != 0 or state.get('job'):
        return {'engine':'automatic', 'status':'busy', 'detail':'Automatic1111 / Forge ocupado: no se descarga su modelo.'}
    await request(session, url + '/sdapi/v1/unload-checkpoint', {})
    return {'engine':'automatic', 'status':'released', 'detail':'Automatic1111 / Forge confirmó la descarga del checkpoint.'}


async def release_idle_backends(session, config):
    async def release(engine, function):
        try:
            return await function(session, config[engine].rstrip('/'))
        except aiohttp.ClientConnectorError:
            return {'engine':engine, 'status':'offline', 'detail':'Motor desconectado.'}
        except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError) as exc:
            return {'engine':engine, 'status':'error', 'detail':f'No se confirmó la liberación de {engine}: {str(exc) or type(exc).__name__}'}
    return {'time':time.time(), 'engines':await asyncio.gather(
        release('comfy', release_comfy), release('automatic', release_automatic))}

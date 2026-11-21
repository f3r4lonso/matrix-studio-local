"""Image controls shared by JSON batches and backend workflows."""
import asyncio
import json
import math
from pathlib import Path
import struct
import aiohttp


EXTRA_DEFAULTS = {'vae':'', 'loras':[], 'sampler':'', 'scheduler':'', 'input_image':'', 'denoise':0.65}


def normalize_customization(settings, engine):
    p = {key: settings.get(key, default) for key, default in EXTRA_DEFAULTS.items()}
    for key in ('vae','sampler','scheduler','input_image'):
        if not isinstance(p[key], str) or len(p[key]) > 500:
            raise ValueError(f'{key} debe ser texto de hasta 500 caracteres.')
    if type(p['denoise']) not in (int,float) or not math.isfinite(p['denoise']) or not 0 < p['denoise'] <= 1:
        raise ValueError('La transformación debe ser mayor que 0 y menor o igual que 1.')
    if not isinstance(p['loras'], list) or len(p['loras']) > 8:
        raise ValueError('Selecciona hasta ocho LoRAs.')
    normalized = []
    for item in p['loras']:
        if not isinstance(item, dict) or not isinstance(item.get('name'), str) or not item['name']:
            raise ValueError('Cada LoRA requiere name y sus intensidades.')
        strength = item.get('strength_model', item.get('strength', 1))
        clip = item.get('strength_clip', strength)
        if any(type(v) not in (int,float) or not math.isfinite(v) or not -2 <= v <= 2 for v in (strength,clip)):
            raise ValueError('Las intensidades LoRA deben estar entre -2 y 2.')
        if engine == 'automatic' and (clip != strength or any(c in item['name'] for c in '<>:\r\n')):
            raise ValueError('Automatic1111 / Forge usa una intensidad común para modelo y CLIP y un nombre LoRA sin etiquetas.')
        normalized.append({'name':item['name'], 'strength_model':float(strength), 'strength_clip':float(clip)})
    if len({i['name'] for i in normalized}) != len(normalized):
        raise ValueError('No añadas la misma LoRA dos veces.')
    p['loras'] = normalized
    if engine == 'qwen' and (p['loras'] or p['vae'] or p['input_image'] or p['sampler'] not in ('','euler') or p['scheduler']):
        raise ValueError('El flujo Qwen actual utiliza su VAE y sampler fijos; LoRAs e imagen inicial se admiten con ComfyUI o Automatic1111 / Forge.')
    return p


def architecture(name, metadata=None):
    text = str(name).lower()
    # Some video adapters contain misleading SD 1.5 metadata: honor their actual family first.
    if any(s in text for s in ('wan2','wan_','wan-','aether_punch','wugong','motion_fix','lightx2v')):return 'wan'
    if 'z_image' in text or 'z-image' in text or 'zimage' in text:return 'zimage'
    if 'flux' in text or Path(text).name == 'ae.safetensors':return 'flux'
    if 'qwen' in text:return 'qwen'
    if 'trellis' in text or 'minimax' in text:return 'other'
    if metadata:
        text += ' ' + ' '.join(str(value).lower() for key,value in metadata.items() if key in ('ss_base_model_version','ss_sd_model_name','modelspec.architecture'))
    if any(s in text for s in ('sdxl','sd_xl','-xl','_xl','ghostxl','ghost_xl','dreamshaperxl','pony','juggernaut')):return 'sdxl'
    if any(s in text for s in ('sd_1.5','sd_v1','sd1.5','sd15','dreamshaper_8','realisticvision','realistic_vision','epicrealism','epicrealism','ghostmix','revanimated','rev_animated','vae-ft-mse')):return 'sd15'
    return 'unknown'


def local_metadata(root, folder, name):
    base = (root/'Data/Models'/folder).resolve()
    path = (base/name).resolve()
    if not path.is_relative_to(base) or not path.is_file() or path.suffix != '.safetensors':return {}
    try:
        with path.open('rb') as stream:
            size = struct.unpack('<Q', stream.read(8))[0]
            if size > 16*1024**2:return {}
            return json.loads(stream.read(size)).get('__metadata__', {})
    except (OSError,ValueError,struct.error):return {}


async def get_json(session, url, optional=False):
    try:
        async with session.get(url, allow_redirects=False, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if optional and response.status == 404:return None
            if response.status != 200:raise ValueError(f'No se pudieron leer las opciones del motor: HTTP {response.status}')
            return await response.json()
    except (aiohttp.ClientError,TimeoutError) as exc:
        raise ValueError('Conecta el motor para cargar modelos, VAE y LoRAs.') from exc


async def discover_options(session, config, root, engine):
    if engine == 'qwen':
        return {'engine':engine,'driver':'qwen','models':[{'name':'Qwen Image 2.1 Turbo','architecture':'qwen'}],
                'loras':[],'vaes':[],'samplers':[],'schedulers':[],'supports_reference':False}
    if engine not in ('comfy','automatic'):raise ValueError('Selecciona un motor válido.')
    url = config[engine]
    if engine == 'comfy':
        ckpt,lora,vae,sampler = await asyncio.gather(*(get_json(session,url+'/object_info/'+node) for node in ('CheckpointLoaderSimple','LoraLoader','VAELoader','KSampler')))
        models = ckpt['CheckpointLoaderSimple']['input']['required']['ckpt_name'][0]
        loras = [{'name':n,'metadata':local_metadata(root,'Lora',n)} for n in lora['LoraLoader']['input']['required']['lora_name'][0]]
        vaes = vae['VAELoader']['input']['required']['vae_name'][0]
        sampler_fields = sampler['KSampler']['input']['required']
        samplers,schedulers = sampler_fields['sampler_name'][0],sampler_fields['scheduler'][0]
        driver = 'comfy'
    else:
        model_data,lora_data,sampler_data,scheduler_data = await asyncio.gather(*(get_json(session,url+path) for path in ('/sdapi/v1/sd-models','/sdapi/v1/loras','/sdapi/v1/samplers','/sdapi/v1/schedulers')))
        models = [m['title'] for m in model_data]
        loras = [{'name':m['name'],'metadata':m.get('metadata') or local_metadata(root,'Lora',Path(m.get('path',m['name'])).name)} for m in lora_data]
        modules = await get_json(session,url+'/sdapi/v1/sd-modules',optional=True)
        driver = 'forge' if modules is not None else 'automatic'
        modules = modules if modules is not None else await get_json(session,url+'/sdapi/v1/sd-vae')
        vaes = [v['model_name'] for v in modules]
        samplers,schedulers = [v['name'] for v in sampler_data],[v['name'] for v in scheduler_data]
    return {'engine':engine,'driver':driver,'models':[{'name':n,'architecture':architecture(n)} for n in models],
            'loras':[{'name':v['name'],'architecture':architecture(v['name'],v['metadata'])} for v in loras],
            'vaes':[{'name':n,'architecture':architecture(n)} for n in vaes],
            'samplers':samplers,'schedulers':schedulers,'supports_reference':True}


def validate_selection(p, options):
    models = {m['name']:m['architecture'] for m in options['models']}
    if p['model'] not in models:raise ValueError('El modelo seleccionado no está disponible en ese motor.')
    family = models[p['model']]
    for field, collection in (('sampler','samplers'),('scheduler','schedulers')):
        if p.get(field) and p[field] not in options[collection]:raise ValueError(f'{field} no está disponible en ese motor.')
    for item in p.get('loras',[]):
        adapter = next((v for v in options['loras'] if v['name'] == item['name']),None)
        if not adapter or family not in ('sd15','sdxl') or adapter['architecture'] != family:
            raise ValueError(f'LoRA incompatible o de arquitectura sin verificar: {item["name"]}.')
    if p.get('vae'):
        vae = next((v for v in options['vaes'] if v['name'] == p['vae']),None)
        if not vae or family not in ('sd15','sdxl') or vae['architecture'] != family:
            raise ValueError('El VAE no corresponde a la arquitectura del modelo. Puedes usar el VAE del checkpoint.')


def image_workflow(p, prompt, image_name=None):
    graph = {
        '1':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':p['model']}},
        '2':{'class_type':'CLIPTextEncode','inputs':{'text':prompt,'clip':['1',1]}},
        '3':{'class_type':'CLIPTextEncode','inputs':{'text':p['negative'],'clip':['1',1]}},
        '4':{'class_type':'EmptyLatentImage','inputs':{'width':p['width'],'height':p['height'],'batch_size':1}},
        '5':{'class_type':'KSampler','inputs':{'seed':p['seed'],'steps':p['steps'],'cfg':p['cfg'],
            'sampler_name':p.get('sampler') or 'euler','scheduler':p.get('scheduler') or 'normal','denoise':1,
            'model':['1',0],'positive':['2',0],'negative':['3',0],'latent_image':['4',0]}},
        '6':{'class_type':'VAEDecode','inputs':{'samples':['5',0],'vae':['1',2]}},
        '7':{'class_type':'SaveImage','inputs':{'images':['6',0],'filename_prefix':'MatrixStudio/image'}}}
    model,clip,vae = ['1',0],['1',1],['1',2]
    for index,adapter in enumerate(p.get('loras',[])):
        key = f'image_lora_{index}'
        graph[key] = {'class_type':'LoraLoader','inputs':{'model':model,'clip':clip,'lora_name':adapter['name'],
            'strength_model':adapter['strength_model'],'strength_clip':adapter['strength_clip']}}
        model,clip = [key,0],[key,1]
    if p.get('vae'):
        graph['image_vae'] = {'class_type':'VAELoader','inputs':{'vae_name':p['vae']}}
        vae = ['image_vae',0]
    graph['2']['inputs']['clip'] = clip;graph['3']['inputs']['clip'] = clip
    graph['5']['inputs']['model'] = model;graph['6']['inputs']['vae'] = vae
    if image_name:
        graph['image_reference'] = {'class_type':'LoadImage','inputs':{'image':image_name}}
        graph['image_resize'] = {'class_type':'ImageScale','inputs':{'image':['image_reference',0],'width':p['width'],'height':p['height'],'upscale_method':'lanczos','crop':'center'}}
        graph['4'] = {'class_type':'VAEEncode','inputs':{'pixels':['image_resize',0],'vae':vae}}
        graph['5']['inputs']['denoise'] = p.get('denoise',.65)
    return graph

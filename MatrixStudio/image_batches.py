"""Persistent, atomic JSON image batches; render rows remain the source of progress."""
import hashlib
import json
import math
import random
import time
import uuid
from image_customization import normalize_customization, EXTRA_DEFAULTS


def normalize_batch(data):
    outer = data if isinstance(data, dict) and 'document' in data else None
    if outer is not None:
        data = outer['document']
    if isinstance(data, list):
        data = {'name': 'Lote JSON', 'prompts': data}
    elif isinstance(data, dict) and 'prompt' in data:
        data = {'name': data.get('nombre', data.get('name', 'Lote JSON')), 'prompts': [data], 'settings': data.get('settings', {})}
    if not isinstance(data, dict):
        raise ValueError('El JSON debe contener una imagen, una lista de imágenes o un objeto con prompts.')
    name = data.get('name', data.get('nombre', 'Lote JSON'))
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        raise ValueError('El nombre del lote debe tener entre 1 y 120 caracteres.')
    entries = data.get('prompts')
    if not isinstance(entries, list) or not 1 <= len(entries) <= 1000:
        raise ValueError('Incluye entre 1 y 1000 elementos en prompts.')
    items = []
    for index, entry in enumerate(entries, 1):
        if isinstance(entry, str):
            entry = {'name': f'Imagen {index}', 'prompt': entry}
        if not isinstance(entry, dict):
            raise ValueError(f'Elemento {index}: se esperaba un nombre y un prompt.')
        title = entry.get('name', entry.get('nombre', f'Imagen {index}'))
        prompt = entry.get('prompt')
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
            raise ValueError(f'Elemento {index}: nombre vacío o demasiado largo.')
        if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 12000:
            raise ValueError(f'Elemento {index}: prompt de entre 1 y 12000 caracteres requerido.')
        item = {'name': title.strip(), 'prompt': prompt.strip()}
        if 'negative_prompt' in entry or 'negative' in entry:
            negative = entry.get('negative_prompt', entry.get('negative'))
            if not isinstance(negative, str) or len(negative) > 12000:
                raise ValueError(f'Elemento {index}: negative_prompt debe ser texto de hasta 12000 caracteres.')
            item['negative'] = negative
        for key in ('numero', 'numero_pokedex'):
            if key in entry:
                value = entry[key]
                if type(value) not in (str, int) or len(str(value)) > 40:
                    raise ValueError(f'Elemento {index}: {key} debe ser texto o entero de hasta 40 caracteres.')
                item[key] = value
        items.append(item)
    settings = data.get('settings', {})
    if not isinstance(settings, dict):
        raise ValueError('settings debe ser un objeto.')
    if outer is not None:
        if not isinstance(outer.get('settings', {}), dict):
            raise ValueError('settings debe ser un objeto.')
        settings = ({**settings, **outer.get('settings', {})} if outer.get('prefer_ui_settings') else {**outer.get('settings', {}), **settings})
    p = {key: settings.get(key, default) for key, default in {
        'engine': 'comfy', 'model': '', 'negative': '', 'width': 512, 'height': 512,
        'steps': 20, 'cfg': 7, 'seed': -1}.items()}
    if p['engine'] not in ('comfy', 'automatic', 'qwen'):
        raise ValueError('Selecciona un motor válido.')
    if not isinstance(p['model'], str) or not isinstance(p['negative'], str) or len(p['negative']) > 12000:
        raise ValueError('Modelo y negativo deben ser texto.')
    for key in ('width', 'height', 'steps', 'seed'):
        if type(p[key]) is not int:
            raise ValueError(f'{key} debe ser un número entero.')
    if type(p['cfg']) not in (int, float) or not math.isfinite(p['cfg']):
        raise ValueError('CFG debe ser un número finito.')
    if any(not 256 <= p[k] <= 2048 or p[k] % 32 for k in ('width', 'height')):
        raise ValueError('Dimensiones: múltiplos de 32 entre 256 y 2048.')
    if not 1 <= p['steps'] <= 150 or not 0 <= p['cfg'] <= 30 or not -1 <= p['seed'] <= 2147483647:
        raise ValueError('Ajustes fuera de rango.')
    if p['engine'] != 'qwen' and not p['model'].strip():
        raise ValueError('Selecciona un modelo en Ajustes antes de importar el lote.')
    p['cfg'] = float(p['cfg'])
    p.update(normalize_customization(settings, p['engine']))
    return {'name': name.strip(), 'prompts': items, 'settings': p}


def store_batch(db, batch):
    # Omit default extensions from the identity to preserve pre-customization batch deduplication.
    identity = {**batch, 'settings':{key:value for key,value in batch['settings'].items() if key not in EXTRA_DEFAULTS or value != EXTRA_DEFAULTS[key]}}
    fingerprint = hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    existing = db.execute('SELECT id,chat_id FROM image_batches WHERE fingerprint=?', (fingerprint,)).fetchone()
    if existing:
        return {'id': existing['id'], 'chat': existing['chat_id'], 'existing': True}, []
    bid, cid, now = uuid.uuid4().hex, uuid.uuid4().hex, time.time()
    ids = []
    total = len(batch['prompts'])
    with db:
        db.execute('INSERT INTO chats (id,title,created) VALUES (?,?,?)', (cid, batch['name'], now))
        db.execute('INSERT INTO image_batches (id,chat_id,name,fingerprint,created) VALUES (?,?,?,?,?)',
                   (bid, cid, batch['name'], fingerprint, now))
        for index, item in enumerate(batch['prompts'], 1):
            rid = uuid.uuid4().hex
            seed = batch['settings']['seed']
            seed = random.randrange(2147483648) if seed == -1 else (seed + index - 1) % 2147483648
            params = {**batch['settings'], 'seed': seed, 'image_batch_id': bid,
                      'item_name': item['name'], 'batch_index': index, 'batch_count': total,
                      'negative': item.get('negative', batch['settings']['negative'])}
            params.update({key: item[key] for key in ('numero', 'numero_pokedex') if key in item})
            db.execute('INSERT INTO renders (id,chat_id,prompt,params,status,detail,image,created) VALUES (?,?,?,?,?,?,?,?)',
                       (rid, cid, item['prompt'], json.dumps(params), 'queued',
                        f'En cola · {index}/{total} · {item["name"]}', None, now))
            ids.append(rid)
    return {'id': bid, 'chat': cid, 'existing': False}, ids


def batch_summaries(db):
    batches = [dict(r) for r in db.execute('SELECT id,chat_id,name,created FROM image_batches ORDER BY created DESC')]
    for batch in batches:
        items = []
        for row in db.execute('SELECT id,params,status,detail,image,image_deleted FROM renders WHERE chat_id=? ORDER BY rowid', (batch['chat_id'],)):
            p = json.loads(row['params'])
            if p.get('image_batch_id') == batch['id']:
                items.append({'id': row['id'], 'name': p['item_name'], 'index': p['batch_index'],
                              'numero': p.get('numero'), 'numero_pokedex': p.get('numero_pokedex'),
                              'status': row['status'], 'detail': row['detail'], 'image': row['image'],
                              'deleted': bool(row['image_deleted'])})
        settings_row = db.execute("SELECT params FROM renders WHERE chat_id=? ORDER BY CASE WHEN status IN ('queued','paused','error') THEN 0 ELSE 1 END,rowid LIMIT 1", (batch['chat_id'],)).fetchone()
        if settings_row:
            saved = json.loads(settings_row['params'])
            keys = ('engine','model','width','height','steps','cfg','seed','negative',*EXTRA_DEFAULTS)
            batch['settings'] = {key:saved[key] for key in keys if key in saved}
        batch['items'] = items
        batch['total'] = len(items)
        batch['done'] = sum(item['status'] == 'done' for item in items)
    return batches

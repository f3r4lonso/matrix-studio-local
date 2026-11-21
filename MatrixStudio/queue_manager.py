"""Persistent ordering, individual editing and cancellation for Studio's queue."""
import asyncio
import json
import math
import random
import uuid
from aiohttp import web

QUEUE_ORDER = 'queue_priority DESC, COALESCE(queue_order,rowid), rowid'
WAITING = ('queued','paused','error')


def interruption_values(db, rid):
    row = db.execute('SELECT cancel_requested FROM renders WHERE id=?',(rid,)).fetchone()
    if row and row['cancel_requested']:
        return {'status':'cancelled','detail':'Cancelado por el usuario. No se retomará automáticamente.'}
    return {'status':'paused','detail':'Generación detenida. Continuar reintenta el elemento o escena con la misma semilla.'}


def editable(ctx, app, rid, include_cancelled=True):
    found = ctx['rows']('SELECT * FROM renders WHERE id=?',(rid,))
    if not found:raise ValueError('Trabajo no encontrado.')
    row = found[0]
    if app.get('active_id') == rid or row['status']=='running':
        raise ValueError('El trabajo activo no admite cambios. Deténlo antes de editar o cambiar su prioridad.')
    allowed = (*WAITING,'cancelled') if include_cancelled else WAITING
    if row['status'] not in allowed:
        raise ValueError('Solo se pueden modificar trabajos pendientes.')
    return row


def ids_from(data):
    values = data.get('ids') if isinstance(data,dict) else None
    if not isinstance(values,list) or not 1 <= len(values) <= 10000:
        raise ValueError('Selecciona entre 1 y 10000 trabajos.')
    if any(not isinstance(v,str) or len(v)!=32 or any(c not in '0123456789abcdef' for c in v) for v in values):
        raise ValueError('Identificador de trabajo inválido.')
    return list(dict.fromkeys(values))


async def cancel_active(app, ctx, rid, was_running, version):
    await ctx['stop_active_generation'](app)
    if app.get('queue_error'):
        ctx['DB'].execute('UPDATE renders SET cancel_requested=0 WHERE id=?',(rid,));ctx['DB'].commit()
        return
    if was_running and app.get('queue_control_version',0)==version:
        ctx['DB'].execute("INSERT OR REPLACE INTO studio_settings (key,value) VALUES ('queue_paused','0')")
        ctx['DB'].commit();app['queue_gate'].set()


def validate_video(ctx, p, patch):
    allowed = {'negative','width','height','steps','cfg','seed','shift','denoise','frames','fps','interpolation','duration_seconds','scene_prompts'}
    if set(patch)-allowed:raise ValueError('En vídeos se edita el prompt y los parámetros; el motor y la arquitectura se conservan.')
    p = {**p,**patch}
    animated = p.get('backend')=='animatediff'
    for key in ('width','height','steps','seed','frames','fps','interpolation'):
        if type(p.get(key)) is not int:raise ValueError(f'{key} debe ser entero.')
    if not 0 <= p['seed'] <= 2147483647:raise ValueError('La semilla debe estar entre 0 y 2147483647.')
    for key in ('cfg','shift','denoise'):
        if key in p and (type(p[key]) not in (int,float) or not math.isfinite(p[key])):raise ValueError(f'{key} debe ser finito.')
    if animated:
        if any(not 128<=p[k]<=768 or p[k]%8 for k in ('width','height')) or not 4<=p['frames']<=64 or not 4<=p['fps']<=30:
            raise ValueError('AnimateDiff: resolución 128–768 múltiplo de 8, 4–64 fotogramas y 4–30 FPS.')
        if not 4<=p['steps']<=50 or not 1<=p['cfg']<=20 or not .05<=p.get('denoise',1)<=1 or p['interpolation'] not in (1,2,3):raise ValueError('Ajustes AnimateDiff fuera de rango.')
    else:
        if any(not 256<=p[k]<=1280 or p[k]%32 for k in ('width','height')) or not 9<=p['frames']<=121 or (p['frames']-1)%8:
            raise ValueError('Wan: resolución 256–1280 múltiplo de 32 y 9–121 fotogramas de la forma 8n+1.')
        if p['fps'] != (24 if p.get('family')=='wan5b' else 16):raise ValueError('Se conservan los FPS nativos de la familia Wan.')
        if not 4<=p['steps']<=60 or not 1<=p['cfg']<=8 or not 1<=p.get('shift',5)<=12 or p['interpolation'] not in (1,2):raise ValueError('Ajustes Wan fuera de rango.')
        p['vae_decode'] = 'spatial_only_full_time' if p['width']*p['height']>512*512 else 'native'
    if p['interpolation']>1 and not (ctx['ROOT']/'Data/Models/FrameInterpolation'/ctx['ANIMATEDIFF_NAMES']['interpolation']).is_file():raise ValueError('RIFE no está instalado.')
    duration=p.get('duration_seconds',0);scenes=p.get('scene_prompts',[])
    for key in ('duration_seconds','output_fps','output_frames','segment_count','scene_prompts'):p.pop(key,None)
    ctx['configure_montage'](p,{'duration_seconds':duration,'scene_prompts':scenes})
    return p


def install_queue_routes(app, ctx):
    async def jobs(request):
        names = {r['id']:r['name'] for r in ctx['rows']('SELECT id,name FROM image_batches')}
        result=[]
        for row in ctx['rows']("SELECT r.*,c.title AS chat_title FROM renders r LEFT JOIN chats c ON c.id=r.chat_id WHERE r.status IN ('queued','paused','running','error','cancelled') OR r.id=? ORDER BY r.queue_priority DESC,COALESCE(r.queue_order,r.rowid),r.rowid",(app.get('active_id') or '',)):
            p=json.loads(row['params']);kind=p.get('kind','image');group=p.get('image_batch_id') or row['chat_id'] or row['id']
            preview='/inputs/'+p['input_image'] if p.get('input_image') else None
            result.append({'id':row['id'],'title':row.get('queue_title') or p.get('item_name') or row['prompt'][:90],
                'prompt':row['prompt'],'params':p,'kind':kind,'status':row['status'],'detail':row['detail'],
                'priority':row['queue_priority'],'active':row['id']==app.get('active_id'),
                'cancel_requested':bool(row['cancel_requested']),'preview':preview,'group_id':group,
                'group_title':names.get(p.get('image_batch_id')) or row['chat_title'] or 'Creación individual',
                'batch_id':p.get('image_batch_id')})
        return web.json_response({'jobs':result,'active_id':app.get('active_id')})

    async def cancel(request):
        data=await request.json();ids=ids_from(data);pending_only=data.get('pending_only',False)
        if type(pending_only) is not bool:raise ValueError('pending_only debe ser booleano.')
        active=None;changed=[];db=ctx['DB']
        with db:
            for rid in ids:
                found=ctx['rows']('SELECT status FROM renders WHERE id=?',(rid,))
                if not found or found[0]['status'] in ('done','cancelled'):continue
                if found[0]['status']=='running' and app.get('active_id')!=rid:
                    raise ValueError('Este trabajo pertenece a otra instancia activa; contrólalo desde esa instancia.')
                if app.get('active_id')==rid:
                    if pending_only:continue
                    if app.get('stopping'):raise ValueError('Ya se está deteniendo un trabajo; espera su confirmación.')
                    active=rid
                    db.execute('UPDATE renders SET cancel_requested=1,detail=? WHERE id=?',('Cancelando generación activa…',rid))
                else:
                    db.execute("UPDATE renders SET status='cancelled',cancel_requested=1,detail='Cancelado por el usuario. No se retomará automáticamente.' WHERE id=?",(rid,))
                changed.append(rid)
        if active:
            was_running=app['queue_gate'].is_set();version=app.get('queue_control_version',0)
            ctx['pause_generation_queue'](app);app['stop_requested']=active;app['stopping']=True;app['queue_error']=''
            app['stop_control_task']=asyncio.create_task(cancel_active(app,ctx,active,was_running,version))
        return web.json_response({'cancelled':changed,'stopping':active})

    async def priority(request):
        data=await request.json();ids=ids_from(data)
        for rid in ids:editable(ctx,app,rid,False)
        db=ctx['DB'];move=data.get('move')
        with db:
            if move:
                if len(ids)!=1 or move not in ('first','up','down','last'):raise ValueError('Elige una posición válida para un trabajo.')
                ordered=ctx['rows']("SELECT id,queue_priority FROM renders WHERE status IN ('queued','paused','error') ORDER BY "+QUEUE_ORDER)
                current=next(i for i,r in enumerate(ordered) if r['id']==ids[0])
                target={'first':0,'last':len(ordered)-1,'up':max(0,current-1),'down':min(len(ordered)-1,current+1)}[move]
                level=ordered[target]['queue_priority'];selected=ordered.pop(current);ordered.insert(target,selected)
                db.execute('UPDATE renders SET queue_priority=? WHERE id=?',(level,ids[0]))
                for index,row in enumerate(ordered):db.execute('UPDATE renders SET queue_order=? WHERE id=?',(index+1,row['id']))
            else:
                value=data.get('priority')
                if type(value) is not int or not -100<=value<=100:raise ValueError('Prioridad: un entero entre -100 y 100.')
                for rid in ids:db.execute('UPDATE renders SET queue_priority=? WHERE id=?',(value,rid))
        return web.json_response({'updated':ids})

    async def requeue(request):
        ids=ids_from(await request.json())
        for rid in ids:editable(ctx,app,rid)
        with ctx['DB']:
            for rid in ids:ctx['DB'].execute("UPDATE renders SET status='queued',cancel_requested=0,detail='En cola para reintentar con los ajustes guardados' WHERE id=?",(rid,))
        for rid in ids:ctx['queue_render'](app,rid)
        return web.json_response({'queued':ids,'paused':not app['queue_gate'].is_set()})

    async def edit(request):
        rid=request.match_info['id'];old=editable(ctx,app,rid);data=await request.json()
        if not isinstance(data,dict):raise ValueError('Se esperaba un objeto con prompt y params.')
        prompt=data.get('prompt',old['prompt']);title=data.get('title',old.get('queue_title') or '')
        if not isinstance(prompt,str) or not 1<=len(prompt.strip())<=12000:raise ValueError('Prompt: entre 1 y 12000 caracteres.')
        if not isinstance(title,str) or len(title)>120:raise ValueError('Título: hasta 120 caracteres.')
        patch=data.get('params',{})
        if not isinstance(patch,dict):raise ValueError('params debe ser un objeto.')
        original=json.loads(old['params']);kind=original.get('kind','image')
        if kind=='image':
            allowed={'engine','model','negative','width','height','steps','cfg','seed','vae','loras','sampler','scheduler','input_image','denoise'}
            if set(patch)-allowed:raise ValueError('Se intentaron cambiar metadatos internos del trabajo.')
            settings=ctx['normalize_batch']({'name':'Edición','prompts':[{'prompt':prompt}],'settings':{**original,**patch}})['settings']
            if settings['seed']==-1:settings['seed']=random.randrange(2147483648)
            await ctx['validate_image_controls'](app,settings)
            p={**original,**settings}
            if title.strip():p['item_name']=title.strip()
        elif kind=='video':p=validate_video(ctx,original,patch)
        else:
            if set(patch)-{'steps','faces','seed'}:raise ValueError('En 3D se pueden editar pasos, caras objetivo y semilla.')
            p={**original,**patch}
            if any(type(p.get(k)) is not int for k in ('steps','faces','seed')) or not 4<=p['steps']<=30 or not 10000<=p['faces']<=500000 or not 0<=p['seed']<=2147483647:raise ValueError('Ajustes 3D fuera de rango.')
        if not isinstance(p.get('negative',''),str) or len(p.get('negative',''))>12000:raise ValueError('Negativo: hasta 12000 caracteres.')
        editable(ctx,app,rid)
        project=ctx['VIDEO_PROJECTS']/rid;backup=None
        try:
            if original.get('duration_seconds') and project.exists() and (p!=original or prompt.strip()!=old['prompt']):
                base=ctx['VIDEO_PROJECTS'].resolve();backup=base/(rid+'-before-edit-'+uuid.uuid4().hex)
                if not project.resolve().is_relative_to(base) or not backup.resolve().is_relative_to(base):raise ValueError('Ruta de escenas no válida.')
                project.rename(backup)
            with ctx['DB']:
                ctx['DB'].execute('UPDATE renders SET prompt=?,params=?,queue_title=?,detail=? WHERE id=?',
                    (prompt.strip(),json.dumps(p),title.strip() or None,'Ajustes editados; conserva su estado en la cola',rid))
        except Exception:
            if backup and backup.exists() and not project.exists():backup.rename(project)
            raise
        return web.json_response({'id':rid,'status':old['status'],'archived_scenes':bool(backup)})

    app.router.add_get('/api/queue/jobs',jobs)
    app.router.add_post('/api/queue/cancel',cancel)
    app.router.add_post('/api/queue/priority',priority)
    app.router.add_post('/api/queue/requeue',requeue)
    app.router.add_post('/api/queue/jobs/{id:[a-f0-9]{32}}/edit',edit)

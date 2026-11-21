const $ = s => document.querySelector(s);
const icons = {
 motion:'M3 4h18v16H3zM7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4m-7-6 3 3-3 3Z',cube:'m12 2 9 5v10l-9 5-9-5V7ZM3 7l9 5 9-5M12 12v10',video:'M3 5h12v14H3zM15 10l6-4v12l-6-4',trash:'M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7',plus:'M12 5v14M5 12h14',sparkles:'m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z M20 2v4M18 4h4',
 grid:'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',layers:'m12 3 10 5-10 5L2 8ZM2 12l10 5 10-5M2 16l10 5 10-5',
 shield:'m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6ZM8 12l3 3 5-6',lock:'M6 10h12v11H6zM8 10V6a4 4 0 0 1 8 0v4',
 sliders:'M4 4v5m0 5v6M12 4v9m0 5v2M20 4v2m0 5v9M1 9h6M9 18h6M17 6h6',square:'M4 4h16v16H4z',
 close:'m6 6 12 12M6 18 18 6',menu:'M3 6h18M3 12h18M3 18h18',refresh:'M20 10a8 8 0 1 0-1 7M20 4v6h-6',
 download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',copy:'M8 8h13v13H8zM16 8V3H3v13h5',info:'M12 8h.01M12 11v6M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z'
};
function icon(name){return `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${icons[name]||icons.sparkles}"/></svg>`;}
document.querySelectorAll('[data-icon]').forEach(e=>e.outerHTML=icon(e.dataset.icon));
const names={qwen:'Qwen Image',comfy:'ComfyUI',automatic:'Automatic1111 / Forge'};
const listCache=new WeakMap();
const state={chat:null,view:'create',engines:[],config:{},renders:[],busy:false};
const esc = t => String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,body){const r=await fetch('/api/'+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});if(r.status===404&&['image-batches','image-options'].includes(path.split('?')[0]))throw Error('La instancia abierta todavía no tiene activa la función Lotes JSON. Reinicia el servidor de Matrix Studio; recargar la pestaña no actualiza Python.');if(!r.headers.get('Content-Type')?.includes('application/json'))throw Error('El servidor no pudo completar la petición. Revisa la consola de Matrix Studio.');const data=await r.json();if(!r.ok)throw Error(data.error||'No se pudo completar la petición.');return data;}
function toast(message){$('#toast').textContent=message;$('#toast').hidden=false;clearTimeout(state.toast);state.toast=setTimeout(()=>$('#toast').hidden=true,6500);}
function setView(view){state.view=view;document.querySelectorAll('.view').forEach(e=>e.hidden=e.id!==view+'-view');document.querySelectorAll('[data-view]').forEach(e=>e.classList.toggle('active',e.dataset.view===view));$('#page-label').textContent={create:'Crear imágenes',gallery:'Mi galería',engines:'Motores',video:'Crear vídeo',mesh:'Crear 3D',animatediff:'AnimateDiff',batches:'Lotes JSON'}[view];$('#sidebar').classList.remove('open');if(view==='batches'){settings(false);loadImageBatches();if(typeof loadBatchControls==='function')loadBatchControls();}if(view==='gallery')loadGallery();if(view==='engines')refreshEngines();if(view==='video'){settings(false);loadVideoStatus();loadVideos();}if(view==='mesh'){settings(false);loadMeshStatus();loadMeshes();}if(view==='animatediff'){settings(false);loadAdStatus();loadAdVideos();}}
function newChat(){state.chat=null;state.renders=[];$('#welcome').hidden=false;$('#conversation').innerHTML='';$('#prompt').value='';setView('create');loadChats();$('#prompt').focus();window.scrollTo({top:0});}
async function loadChats(){const chats=await api('chats');$('#chat-list').innerHTML=chats.length?chats.map(c=>`<div class="chat-row ${state.chat===c.id?'selected':''}"><button class="chat-item" data-chat="${c.id}" title="${esc(c.title)}">${esc(c.title)}</button><button class="delete-chat icon-button" data-delete-chat="${c.id}" aria-label="Borrar chat: ${esc(c.title)}" title="Borrar chat">${icon('trash')}</button></div>`).join(''):'<p class="history-empty">Tu próxima gran idea<br>empieza aquí.</p>';}
async function openChat(id){state.chat=id;setView('create');await loadConversation();await loadChats();window.scrollTo({top:0});}
function videoDuration(p){return p.duration_seconds||(((p.frames-1)*(p.interpolation||1)+1)/(p.fps*(p.interpolation||1)));}
function videoFps(p){return p.output_fps||p.fps*(p.interpolation||1);}
function media(r,preview=false){if(r.params.kind==='mesh')return `<model-viewer class="result-mesh ${preview?'gallery-mesh':''}" src="${r.image}" alt="${esc(r.prompt)}" camera-controls touch-action="pan-y" shadow-intensity="1" exposure="1" loading="lazy" aria-label="Modelo 3D: ${esc(r.prompt)}"></model-viewer>`;return r.params.kind==='video'?`<video class="${preview?'gallery-video':'result-image'}" src="${r.image}" controls playsinline preload="${preview||r.params.duration_seconds>30?'metadata':'auto'}" style="aspect-ratio:${r.params.width}/${r.params.height}" aria-label="${esc(r.prompt)}"></video>`:`<img class="${preview?'':'result-image'}" src="${r.image}" ${preview?'loading="lazy"':''} alt="${esc(r.prompt)}" data-image="${r.id}">`;}
function actions(r){const video=r.params.kind==='video',mesh=r.params.kind==='mesh',ad=r.params.backend==='animatediff';return `<div class="result-actions">${r.image?`<a href="${r.image}" download="${r.params.item_name?String(r.params.batch_index).padStart(4,'0')+'_'+esc(r.params.item_name.replace(/[^\p{L}\p{N}_.-]+/gu,'_').slice(0,80)):'matrix-'+r.params.seed}.${mesh?'glb':video?'mp4':'png'}">${icon('download')}Descargar${mesh?' GLB':video?' MP4':''}</a>`:''}${mesh?`<button data-mesh-reuse="${r.id}">${icon('refresh')}Crear de nuevo</button>`:video&&ad?`<button data-ad-reuse="${r.id}">${icon('refresh')}Crear otra versión</button>`:video&&r.params.backend==='action_edit'?'':video?`<button data-video-reuse="${r.id}">${icon('refresh')}Animar de nuevo</button>`:`<button data-reuse="${r.id}">${icon('refresh')}Volver a crear</button><button data-variations="${r.id}">${icon('sparkles')}Más variaciones</button>${r.image?`<button data-animate="${r.id}">${icon('video')}Animar imagen</button><button data-ad-reference="${r.id}">${icon('motion')}AnimateDiff</button><button data-model3d="${r.id}">${icon('cube')}Crear modelo 3D</button>`:''}`}${video&&r.status==='done'&&!ad&&r.params.backend!=='action_edit'&&!r.params.duration_seconds&&[81,121].includes(r.params.frames)?`<button data-continue-video="${r.id}">${icon('video')}Continuar boxeo</button>`:''}${video&&r.status==='done'&&r.params.continuation_of&&r.params.backend!=='action_edit'?`<button data-action-assemble="${r.id}">${icon('motion')}Montar pelea 2×</button>`:''}<button data-copy="${r.id}" aria-label="Copiar prompt">${icon('copy')}</button><small>Semilla ${r.params.seed}</small>${r.status==='error'&&r.params.duration_seconds?`<button data-resume-video="${r.id}">${icon('refresh')}Reanudar montaje</button>`:''}${r.image?`<button class="delete-image" data-delete-image="${r.id}">${icon('trash')}Borrar ${mesh?'modelo':video?'vídeo':'imagen'}</button>`:''}</div>`;}
function renderCard(r){const p=r.params;return `<article class="render" data-render="${r.id}"><div class="render-prompt"><div class="prompt-bubble">${esc(r.prompt)}</div><span class="avatar">M</span></div><div class="render-answer"><div class="answer-brand"><span class="small-star">✳</span>Matrix Studio<span class="answer-meta">${esc(['video','mesh'].includes(p.kind)?p.model:names[p.engine])} · ${p.width} × ${p.height}${p.batch_count>1?' · Variación '+p.batch_index+'/'+p.batch_count:''}</span></div>${r.status==='done'?`${media(r)}${actions(r)}`:`<div class="render-status ${r.status==='error'?'error':''}">${['error','deleted','paused'].includes(r.status)?icon('info'):'<span class="spinner"></span>'}<span>${esc(r.detail)}</span></div>${['error','deleted','paused'].includes(r.status)?actions(r):''}`}</div></article>`;}
async function loadConversation(){if(!state.chat)return;const cid=state.chat;const list=await api('renders?chat='+cid);if(state.chat!==cid)return;const changed=JSON.stringify(list)!==JSON.stringify(state.renders);state.renders=list;$('#welcome').hidden=list.length>0;if(changed){updateList('#conversation',list,renderCard,'');if(list.some(r=>r.status==='done'))loadGallery().catch(()=>{});}}
async function refreshEngines(){try{const data=await api('engines');state.engines=data.engines;state.config=data.config;$('#comfy-url').value=data.config.comfy;$('#automatic-url').value=data.config.automatic;updateModel();$('#engine-cards').innerHTML=data.engines.map(e=>`<article class="engine-card">${icon(e.id==='qwen'?'sparkles':'layers')}<h2>${esc(names[e.id])}</h2><p>${{comfy:'Tus checkpoints SD y SDXL, con la flexibilidad de ComfyUI.',qwen:'Qwen Image 2.1 Turbo. Generación local con tu motor CUDA.',automatic:'Conecta la API de tu instalación de Automatic1111 o Forge.'}[e.id]}</p><div class="engine-state ${e.ready?'ready':''}">${e.ready?'● ':''}${esc(e.detail)}</div>${e.id==='comfy'&&!e.ready?'<button class="secondary-button" id="boot-comfy">Iniciar ComfyUI</button>':`<button class="secondary-button" data-select-engine="${e.id}">Usar este motor</button>`}</article>`).join('');}catch(e){toast(e.message);}}
function updateModel(){const engine=$('#engine').value;const current=$('#model').value;const e=state.engines.find(x=>x.id===engine);const models=e?.models||[];$('#model').innerHTML=models.length?models.map(m=>`<option value="${esc(m)}">${esc(m)}</option>`).join(''):'<option value="">Conecta el motor para ver modelos</option>';if(models.includes(current))$('#model').value=current;$('#engine-status').textContent=e?.ready?names[engine]+' · Listo para crear':names[engine]+' · '+(e?.detail||'Actualiza la conexión en Motores');}
function switchEngine(engine){$('#engine').value=engine;$('#steps').value=engine==='qwen'?8:20;$('#cfg').value=engine==='qwen'?1:7;updateModel();savePreferences();}
function savePreferences(){const data={};['engine','size','steps','cfg','seed','negative','count'].forEach(k=>data[k]=$('#'+k).value);try{localStorage.setItem('matrix-preferences',JSON.stringify(data));}catch{}}
function format(){const [w,h]=$('#size').value.split('x').map(Number);$('#format-label').textContent=w===h?'1:1':w/h===1.5?'3:2':h/w===1.5?'2:3':'16:9';savePreferences();}
function settings(show=true){$('#settings-panel').hidden=!show;}
async function submit(event){event.preventDefault();if(state.busy)return;const prompt=$('#prompt').value.trim();if(!prompt)return;const engine=$('#engine').value;if(!state.engines.find(e=>e.id===engine)?.ready){setView('engines');toast('Conecta o inicia el motor seleccionado para generar.');return;}if(!$('#steps').reportValidity()||!$('#cfg').reportValidity()||!$('#seed').reportValidity()){settings();return;}state.busy=true;$('#generate').disabled=true;try{const [width,height]=$('#size').value.split('x').map(Number);const data=await api('generate',{prompt,chat:state.chat,engine,model:$('#model').value,width,height,steps:Number($('#steps').value),cfg:Number($('#cfg').value),seed:Number($('#seed').value),negative:$('#negative').value,count:Number($('#count').value)});state.chat=data.chat;$('#prompt').value='';await loadConversation();await loadChats();document.querySelector('.render:last-child')?.scrollIntoView({behavior:'smooth',block:'start'});savePreferences();}catch(e){toast(e.message);}finally{state.busy=false;$('#generate').disabled=false;}}
function renderOrigin(r){const p=r.params||{},engine=p.engine==='qwen'?'Qwen · stable-diffusion.cpp':names[p.engine]||p.engine||'Motor no registrado',model=p.model||'Modelo no registrado';return `${p.item_name?`<strong class="batch-image-name">${p.batch_index}. ${esc(p.item_name)}</strong>`:''}<div class="gallery-origin"><span class="engine-badge">${esc(engine)}</span><span class="gallery-model" title="${esc(model)}">${esc(model)}</span></div>`;}
async function loadGallery(){
 const requestId=state.galleryRequest=(state.galleryRequest||0)+1;
 const [list,batches]=await Promise.all([api('renders'),api('image-batches').catch(()=>[])]);
 if(requestId!==state.galleryRequest)return;
 state.gallery=list;state.galleryBatches=batches;
 $('#gallery-count').textContent=list.filter(r=>r.status==='done').length;
 renderGalleryCollections();
}

function findRender(id){return state.renders.find(r=>r.id===id)||state.gallery?.find(r=>r.id===id)||state.videoRenders?.find(r=>r.id===id)||state.meshRenders?.find(r=>r.id===id)||state.adRenders?.find(r=>r.id===id);}
document.addEventListener('click',async event=>{const t=event.target.closest('button,a,[data-image]');if(!t)return;try{if(t.dataset.continueVideo){t.disabled=true;try{await api('video/continue',{source_id:t.dataset.continueVideo});await Promise.all([loadVideos(),loadChats()]);toast('Continuación en cola desde el último fotograma.');}finally{t.disabled=false;}return;}if(t.dataset.actionAssemble){const r=findRender(t.dataset.actionAssemble);if(r){t.disabled=true;try{await api('video/assemble',{first_id:r.params.continuation_of,second_id:r.id});await Promise.all([loadVideos(),loadChats()]);toast('Pelea montada a 2×, sin repetir el fotograma de enlace.');}finally{t.disabled=false;}}return;}if(t.dataset.resumeVideo){await api('renders/'+t.dataset.resumeVideo+'/resume',{});await Promise.all([loadConversation(),loadVideos(),loadAdVideos()]);toast('Montaje en cola. Se reutilizarán las escenas terminadas.');return;}if(t.dataset.adReference){const r=findRender(t.dataset.adReference);if(r){state.adSource={render_id:r.id};$('#ad-reference').src=r.image;$('#ad-reference').hidden=false;$('#ad-upload-label').hidden=true;$('#ad-clear-image').hidden=false;$('#ad-mode').value='reference';updateAdMode();setView('animatediff');$('#ad-prompt').focus();}return;}if(t.dataset.adReuse){const r=findRender(t.dataset.adReuse);if(r){await loadAdStatus();state.adSource=r.params.input_image?{input_image:r.params.input_image}:null;$('#ad-mode').value=state.adSource?'reference':'text';if(state.adSource){$('#ad-reference').src='/inputs/'+r.params.input_image;$('#ad-reference').hidden=false;$('#ad-upload-label').hidden=true;$('#ad-clear-image').hidden=false;}$('#ad-prompt').value=r.prompt;$('#ad-duration-seconds').value=String(r.params.duration_seconds||0);$('#ad-scenes').value=(r.params.scene_prompts||[]).join('\n');$('#ad-size').value=r.params.width+'x'+r.params.height;['frames','fps','steps','cfg','denoise','negative'].forEach(k=>$('#ad-'+k).value=r.params[k]);$('#ad-model').value=r.params.model;$('#ad-seed').value=-1;for(const [field,value] of Object.entries({'motion-model':r.params.motion_model||'mm_sd15_v3.safetensors','motion-lora':r.params.motion_lora||'','camera-strength':r.params.motion_lora_strength??0.3,'motion-scale':r.params.motion_scale??1,interpolation:r.params.interpolation||1,sampler:r.params.sampler||'euler',scheduler:r.params.scheduler||'normal'}))$('#ad-'+field).value=value;updateAdCamera();updateAdMode();updateAdDuration();setView('animatediff');}return;}if(t.dataset.model3d){const r=findRender(t.dataset.model3d);if(r){state.meshSource={render_id:r.id};$('#mesh-reference').src=r.image;$('#mesh-reference').hidden=false;$('#mesh-upload-label').hidden=true;setView('mesh');$('#mesh-name').focus();}return;}if(t.dataset.meshReuse){const r=findRender(t.dataset.meshReuse);if(r){state.meshSource={input_image:r.params.input_image};$('#mesh-reference').src='/inputs/'+r.params.input_image;$('#mesh-reference').hidden=false;$('#mesh-upload-label').hidden=true;$('#mesh-name').value=r.prompt;$('#mesh-mode').value=r.params.mode;$('#mesh-steps').value=r.params.steps;$('#mesh-faces').value=r.params.faces;$('#mesh-remove-background').checked=r.params.remove_background;$('#mesh-seed').value=-1;setView('mesh');}return;}if(t.dataset.animate){const r=findRender(t.dataset.animate);if(r){state.videoSource={render_id:r.id};$('#video-reference').src=r.image;$('#video-reference').hidden=false;$('#video-upload-label').hidden=true;setView('video');$('#video-prompt').focus();}return;}if(t.dataset.videoReuse){const r=findRender(t.dataset.videoReuse);if(r){state.videoSource={input_image:r.params.input_image};$('#video-reference').src='/inputs/'+r.params.input_image;$('#video-reference').hidden=false;$('#video-upload-label').hidden=true;$('#video-prompt').value=r.prompt;$('#video-family').value=r.params.family||'wan14b';$('#video-profile').value=r.params.profile||'fast';$('#video-preset').value=r.params.preset||'manual';actionPresetHint(state.actionPresets?.find(p=>p.id===$('#video-preset').value));applyWanProfile();for(const key of ['steps','cfg','shift','negative'])if(r.params[key]!=null)$('#video-'+key).value=r.params[key];$('#video-duration').value=String(r.params.duration_seconds||0);$('#video-scenes').value=(r.params.scene_prompts||[]).join('\n');updateVideoTiming();$('#video-size').value=r.params.width+'x'+r.params.height;$('#video-frames').value=r.params.frames;$('#video-interpolation').value=String(r.params.interpolation||1);$('#video-seed').value=r.params.seed??-1;setView('video');}return;}if(t.dataset.deleteImage||t.dataset.deleteChat){await deleteItem(t.dataset.deleteChat?'chats':'renders',t.dataset.deleteChat||t.dataset.deleteImage);return;}if(t.dataset.view)setView(t.dataset.view);if(t.dataset.chat)await openChat(t.dataset.chat);if(t.dataset.prompt){setView('create');$('#prompt').value=t.dataset.prompt;$('#prompt').focus();}if(t.dataset.selectEngine){switchEngine(t.dataset.selectEngine);setView('create');$('#prompt').focus();}if(t.id==='boot-comfy'||t.id==='start-video-comfy'||t.id==='start-mesh-comfy'||t.id==='start-ad-comfy'){t.disabled=true;try{toast((await api('engines/comfy/start',{})).detail);}finally{t.disabled=false;}setTimeout(refreshEngines,6000);}if(t.dataset.variations){const r=findRender(t.dataset.variations);if(r){$('#image-dialog').close();switchEngine(r.params.engine);$('#prompt').value=r.prompt;['steps','cfg','negative'].forEach(k=>$('#'+k).value=r.params[k]);$('#size').value=r.params.width+'x'+r.params.height;if([...$('#model').options].some(o=>o.value===r.params.model))$('#model').value=r.params.model;$('#seed').value=-1;$('#count').value='4';format();updateCount();setView('create');$('#prompt').focus();toast('Mismo prompt, 4 imágenes con semillas diferentes. Pulsa Generar.');}}if(t.dataset.reuse){$('#image-dialog').close();const r=findRender(t.dataset.reuse);if(r){switchEngine(r.params.engine);$('#prompt').value=r.prompt;['steps','cfg','negative','seed'].forEach(k=>$('#'+k).value=r.params[k]);$('#size').value=r.params.width+'x'+r.params.height;if([...$('#model').options].some(o=>o.value===r.params.model))$('#model').value=r.params.model;format();setView('create');$('#prompt').focus();toast('Prompt y ajustes recuperados. Pulsa Generar para crear otra imagen.');}}if(t.dataset.copy){await navigator.clipboard.writeText(findRender(t.dataset.copy).prompt);toast('Prompt copiado.');}if(t.dataset.describeRender){openRenderDescription(findRender(t.dataset.describeRender));return;}if(t.dataset.image){openRenderDescription(findRender(t.dataset.image));}if(t.id==='first-image')newChat();}catch(e){toast(e.message);}});
$('#new-chat').onclick=newChat;
$('#menu').onclick=()=>$('#sidebar').classList.toggle('open');
$('#toggle-settings').onclick=()=>settings($('#settings-panel').hidden);
$('#composer-settings').onclick=()=>settings($('#settings-panel').hidden);
$('#close-settings').onclick=()=>settings(false);
$('#close-image').onclick=()=>$('#image-dialog').close();
$('#image-dialog').addEventListener('click',e=>{if(e.target===$('#image-dialog'))$('#image-dialog').close();});
$('#engine').onchange=()=>switchEngine($('#engine').value);
$('#size').onchange=format;
$('#format-button').onclick=()=>{const s=$('#size');s.selectedIndex=(s.selectedIndex+1)%s.options.length;format();};
$('#composer').onsubmit=submit;
$('#prompt').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('#composer').requestSubmit();}};
$('#refresh-engines').onclick=async()=>{await refreshEngines();toast('Estado de los motores actualizado.');};
$('#connections').onsubmit=async e=>{e.preventDefault();try{await api('settings',{comfy:$('#comfy-url').value,automatic:$('#automatic-url').value});await refreshEngines();toast('Conexiones guardadas.');}catch(error){toast(error.message);}};
document.addEventListener('keydown',e=>{if(e.key==='Escape'){settings(false);$('#sidebar').classList.remove('open');}if(e.key.toLowerCase()==='n'&&!e.ctrlKey&&!e.metaKey&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();newChat();}});
async function init(){try{const prefs=JSON.parse(localStorage.getItem('matrix-preferences')||'{}');Object.entries(prefs).forEach(([k,v])=>{if(['engine','size','steps','cfg','seed','negative','count'].includes(k))$('#'+k).value=v;});}catch{}format();updateCount();await Promise.all([loadChats(),refreshEngines(),loadGallery(),loadQueueStatus()]);}
init().catch(e=>toast(e.message));
setInterval(async()=>{try{await loadQueueStatus();if(state.chat)await loadConversation();if(state.view==='gallery')await loadGallery();if(state.view==='video'){await loadVideos();await loadVideoStatus();}if(state.view==='mesh'){await loadMeshes();await loadMeshStatus();}if(state.view==='animatediff'){await loadAdVideos();await loadAdStatus();}}catch{}},2000);

async function deleteItem(kind,id){
  const key=kind+'/'+id;
  state.deleting??=new Set();
  if(state.deleting.has(key))return;
  state.deleting.add(key);
  const deletion={kind,id};
  $('#image-dialog').close();
  try{
    await api(`${deletion.kind}/${deletion.id}/delete`,{});
    if(deletion.kind==='chats'&&state.chat===deletion.id)newChat();
    await Promise.all([loadChats(),loadGallery(),loadConversation(),loadVideos(),loadMeshes(),loadAdVideos()]);
    toast(deletion.kind==='chats'?'Chat borrado.':'Elemento borrado.');
    clearTimeout(state.toast);
    const undo=document.createElement('button');
    undo.className='undo-button';undo.textContent='Deshacer';
    undo.onclick=async()=>{try{undo.disabled=true;await api(`${deletion.kind}/${deletion.id}/restore`,{});await Promise.all([loadChats(),loadGallery(),loadConversation(),loadVideos(),loadMeshes(),loadAdVideos()]);toast('Restaurado.');}catch(e){toast(e.message);}};
    $('#toast').append(undo);
    state.toast=setTimeout(()=>$('#toast').hidden=true,15000);
  }catch(e){toast(e.message);}finally{state.deleting.delete(key);}
}

function updateCount(){const count=Number($('#count').value)||1;$('#generate-label').textContent=count>1?'Generar '+count:'Generar';$('#count').title=count>1?'Se generarán '+count+' imágenes una a una, con semillas distintas.':'Generar una imagen';savePreferences();}
$('#count').onchange=updateCount;

function updateVideoTiming(){
 const small=$('#video-family').value==='wan5b',sourceFps=small?24:16,frames=Number($('#video-frames').value),total=Number($('#video-duration').value),profile=$('#video-profile').value,multiplier=Number($('#video-interpolation').value)||1;
 const fps=sourceFps*multiplier,clip=((frames-1)*multiplier+1)/fps,steps=Number($('#video-steps').value),cfg=Number($('#video-cfg').value),shift=Number($('#video-shift').value);
 $('#video-profile-hint').textContent=small?`Wan 5B · ${steps} pasos · UniPC · CFG ${cfg} · shift ${shift} · sin LoRA de aceleración.`:profile==='fast'?'Wan 14B · 4 pasos · CFG 1 · shift 5. Con CFG 1, el prompt negativo no influye.':`Wan 14B · ${steps} pasos · UniPC · CFG ${cfg} · shift ${shift} · sin LightX2V.`;
 $('#video-timing').textContent=total?`${total} segundos · ${Math.ceil(total/clip)} escenas aprox. · ${fps} fps${multiplier>1?' con RIFE':''}. Cada escena tiene hasta ${clip.toLocaleString('es',{maximumFractionDigits:2})} s.`:`Un clip de ${clip.toLocaleString('es',{maximumFractionDigits:2})} s · ${fps} fps${multiplier>1?' con RIFE':''}.`;
}
async function loadVideoStatus(){try{const data=await api('video/status');state.videoStatus=data;loadActionPresets(data.presets||[]);state.videoInterpolationReady=!!data.interpolation_ready;$('#video-interpolation').querySelector('option[value="2"]').disabled=!data.interpolation_ready;if(!$('#video-family').dataset.initialized){$('#video-family').value=data.default_family||'wan14b';$('#video-family').dataset.initialized='true';applyWanProfile();}const family=data.families?.find(f=>f.id===$('#video-family').value);const recipe=data.presets?.find(p=>p.id===$('#video-preset').value);state.videoReady=recipe?recipe.ready:family?($('#video-family').value==='wan14b'&&$('#video-profile').value==='fast'?(family.fast_ready??family.ready):family.ready):data.ready;$('#video-model-status').textContent=( $('#video-family').value==='wan5b'?'Wan 2.2 5B Q5':'Wan 2.2 14B Q3')+(state.videoReady?' · Listo':' · Modelos pendientes de instalar');$('#generate-video').disabled=!state.videoReady||!!state.videoUploading||!!state.videoSubmitting;updateVideoTiming();if(!state.recipeFromUrl){state.recipeFromUrl=true;const wanted=new URLSearchParams(location.search).get('preset');if(data.presets?.some(p=>p.id===wanted&&p.ready)){$('#video-preset').value=wanted;$('#video-preset').onchange();}}}catch(e){$('#video-model-status').textContent=e.message;}}
function loadActionPresets(presets){
 state.actionPresets=presets;
 const select=$('#video-preset'),value=select.value;
 select.innerHTML='<option value="manual">Manual · mis ajustes</option>'+presets.map(p=>`<option value="${esc(p.id)}" ${p.ready?'':'disabled'}>${esc(p.label)}${p.ready?'':' · adaptadores pendientes'}</option>`).join('');
 if([...select.options].some(o=>o.value===value))select.value=value;
}
function actionPresetHint(preset){
 $('#video-preset-hint').textContent=preset?preset.description:'Ajustes manuales. Para usar una LoRA de acción, selecciona una receta.';
 $('#video-reference-guide').hidden=!preset;
 const selected=state.videoRenders?.find(r=>r.params.preset===preset?.id&&r.params.selected_action&&r.params.reference_prompt);$('#video-reference-prompt').textContent=selected?.params.reference_prompt||preset?.image_prompt||'';
}
$('#video-preset').onchange=()=>{
 const preset=state.actionPresets?.find(p=>p.id===$('#video-preset').value);
 actionPresetHint(preset);
 if(!preset)return;
 const p=preset.settings;
 $('#video-family').value=p.family;$('#video-profile').value=p.profile;applyWanProfile();
 for(const key of ['steps','cfg','shift'])$('#video-'+key).value=p[key];
 $('#video-size').value=p.width+'x'+p.height;$('#video-frames').value=String(p.frames);
 $('#video-duration').value='0';$('#video-scenes').value='';$('#video-count').value='1';$('#video-seed').value=String(p.seed??-1);$('#video-interpolation').value=String(p.interpolation||1);
 $('#video-prompt').value=preset.prompt;loadVideoStatus();updateVideoTiming();
};
$('#copy-video-reference-prompt').onclick=async()=>{await navigator.clipboard.writeText($('#video-reference-prompt').textContent);toast('Prompt de imagen copiado. Puedes usarlo en Crear imagen.');};
function manualVideoPreset(){$('#video-preset').value='manual';actionPresetHint(null);}
function applyWanProfile(){const small=$('#video-family').value==='wan5b',profile=$('#video-profile').value;$('#video-size').querySelector('option[value="1280x704"]').disabled=!small;if(!small&&$('#video-size').value==='1280x704')$('#video-size').value='640x384';$('#video-steps').value=profile==='quality'?(small?50:40):profile==='balanced'?20:small?10:4;$('#video-cfg').value=small?5:profile==='fast'?1:3.5;$('#video-shift').value=small?8:profile==='fast'?5:3;for(const key of ['video-steps','video-cfg','video-shift'])$('#'+key).readOnly=!small&&profile==='fast';updateVideoTiming();}
$('#video-family').onchange=()=>{manualVideoPreset();applyWanProfile();loadVideoStatus();};
$('#video-profile').onchange=()=>{manualVideoPreset();applyWanProfile();loadVideoStatus();};
for(const key of ['video-frames','video-duration','video-steps','video-cfg','video-shift','video-interpolation'])$('#'+key).onchange=updateVideoTiming;
async function loadVideos(){const all=await api('renders');const items=all.filter(r=>r.params.kind==='video'&&r.params.backend!=='animatediff');state.videoRenders=items;const wanted=new URLSearchParams(location.search).get('preset');if(wanted&&!state.videoSource){const saved=items.find(r=>r.params.preset===wanted&&r.params.input_image&&r.params.selected_action)||items.find(r=>r.params.preset===wanted&&r.params.input_image);if(saved){state.videoSource={input_image:saved.params.input_image};$('#video-reference').src='/inputs/'+saved.params.input_image;$('#video-reference').hidden=false;$('#video-upload-label').hidden=true;if(saved.params.reference_prompt)$('#video-reference-prompt').textContent=saved.params.reference_prompt;}}updateList('#video-results',items,r=>`<article class="video-result"><div class="answer-brand">${icon('video')}Wan ${r.params.family==='wan5b'?'5B':'14B'} <span class="answer-meta">${r.params.width} × ${r.params.height} · ${videoDuration(r.params).toFixed(1)} s · ${videoFps(r.params)} fps${r.params.batch_count>1?' · '+r.params.batch_index+'/'+r.params.batch_count:''}</span></div><p class="video-hint">${r.params.steps} pasos${r.params.playback_speed===2?' · Montaje a 2×':''}${r.params.interpolation>1?' · RIFE 2×':''} · CFG ${r.params.cfg} · shift ${r.params.shift??5}${r.params.adapter==='motion_fix'?' · Slow-Mo Fix':''}${r.params.action_lora&&r.params.action_lora!=='none'?' · '+esc(r.params.action_lora):''}${r.params.segment_count?' · '+r.params.segment_count+' escenas':''}</p>${r.status==='done'?media(r):`<div class="render-status ${r.status==='error'?'error':''}">${['error','deleted','paused'].includes(r.status)?icon('info'):'<span class="spinner"></span>'}<span>${esc(r.detail)}</span></div>`}<p>${esc(r.prompt)}</p>${actions(r)}</article>`,'<div class="empty-state"><strong>Tu próxima escena empieza aquí.</strong>Prepara una nueva creación para empezar.</div>');}
$('#video-file').onchange=async()=>{const file=$('#video-file').files[0];if(!file)return;state.videoUploading=true;$('#generate-video').disabled=true;try{const form=new FormData();form.append('image',file);const response=await fetch('/api/video/input',{method:'POST',body:form});const result=await response.json();if(!response.ok)throw Error(result.error||'No se pudo subir la imagen local.');state.videoSource={input_image:result.name};$('#video-reference').src=result.url;$('#video-reference').hidden=false;$('#video-upload-label').hidden=true;toast('Imagen preparada en tu equipo.');}catch(e){toast(e.message);}finally{state.videoUploading=false;$('#generate-video').disabled=!state.videoReady;}};
$('#video-form').onsubmit=async e=>{e.preventDefault();if(!state.videoSource){toast('Selecciona la imagen que quieres animar.');return;}if(state.videoUploading||state.videoSubmitting)return;state.videoSubmitting=true;$('#generate-video').disabled=true;try{const [width,height]=$('#video-size').value.split('x').map(Number);const batch=await api('video/generate',{...state.videoSource,preset:$('#video-preset').value,interpolation:Number($('#video-interpolation').value),family:$('#video-family').value,profile:$('#video-profile').value,steps:Number($('#video-steps').value),cfg:Number($('#video-cfg').value),shift:Number($('#video-shift').value),negative:$('#video-negative').value,duration_seconds:Number($('#video-duration').value),scene_prompts:$('#video-scenes').value.split('\n').map(s=>s.trim()).filter(Boolean),prompt:$('#video-prompt').value,width,height,frames:Number($('#video-frames').value),count:Number($('#video-count').value),seed:Number($('#video-seed').value)});await Promise.all([loadVideos(),loadChats()]);toast(batch.count===1?'Vídeo en cola. Se generará en tu equipo.':batch.count+' vídeos en cola, con semillas distintas.');}catch(error){toast(error.message);}finally{state.videoSubmitting=false;$('#generate-video').disabled=!state.videoReady;}};

async function loadMeshStatus(){try{const data=await api('3d/status');state.meshReady=data.ready;const ready=data.models.filter(m=>m.ready).length;const downloaded=data.models.reduce((total,m)=>total+m.downloaded,0);$('#mesh-model-status').textContent=data.ready?'TRELLIS.2 INT8 · 5 modelos instalados':`Instalando TRELLIS.2: ${ready}/5 · ${(downloaded/1e9).toFixed(1)} GB en descarga`;$('#generate-mesh').disabled=!data.ready||!!state.meshUploading||!!state.meshSubmitting;}catch(e){$('#mesh-model-status').textContent=e.message;}}
async function loadMeshes(){const all=await api('renders');const items=all.filter(r=>r.params.kind==='mesh');state.meshRenders=items;updateList('#mesh-results',items,r=>`<article class="video-result"><div class="answer-brand">${icon('cube')}TRELLIS.2 <span class="answer-meta">512³ · ${esc({shape:'Geometría',color:'Color',pbr:'PBR'}[r.params.mode])}</span></div>${r.status==='done'?media(r):`<div class="render-status ${r.status==='error'?'error':''}">${['error','deleted','paused'].includes(r.status)?icon('info'):'<span class="spinner"></span>'}<span>${esc(r.detail)}</span></div>`}<p>${esc(r.prompt)}</p>${actions(r)}</article>`,'<div class="empty-state"><strong>Una imagen. Todas sus caras.</strong>Prepara una nueva creación para empezar.</div>');}
$('#mesh-file').onchange=async()=>{const file=$('#mesh-file').files[0];if(!file)return;state.meshUploading=true;$('#generate-mesh').disabled=true;try{const form=new FormData();form.append('image',file);const response=await fetch('/api/3d/input',{method:'POST',body:form});const result=await response.json();if(!response.ok)throw Error(result.error||'No se pudo preparar la imagen.');state.meshSource={input_image:result.name};$('#mesh-reference').src=result.url;$('#mesh-reference').hidden=false;$('#mesh-upload-label').hidden=true;toast('Referencia 3D preparada en tu equipo.');}catch(e){toast(e.message);}finally{state.meshUploading=false;$('#generate-mesh').disabled=!state.meshReady;}};
$('#mesh-form').onsubmit=async e=>{e.preventDefault();if(!state.meshSource){toast('Selecciona la imagen del objeto.');return;}if(state.meshUploading||state.meshSubmitting)return;state.meshSubmitting=true;$('#generate-mesh').disabled=true;try{await api('3d/generate',{...state.meshSource,name:$('#mesh-name').value,mode:$('#mesh-mode').value,steps:Number($('#mesh-steps').value),faces:Number($('#mesh-faces').value),seed:Number($('#mesh-seed').value),remove_background:$('#mesh-remove-background').checked});await Promise.all([loadMeshes(),loadChats()]);toast('Modelo 3D en cola. Se generará en tu GPU.');}catch(error){toast(error.message);}finally{state.meshSubmitting=false;$('#generate-mesh').disabled=!state.meshReady;}};

function updateAdMode(){const reference=$('#ad-mode').value==='reference';$('#ad-reference-fields').hidden=!reference;$('#ad-transform-fields').hidden=!reference;}
function updateAdDuration(){const frames=Number($('#ad-frames').value),fps=Number($('#ad-fps').value),multiplier=Number($('#ad-interpolation').value),total=Number($('#ad-duration-seconds').value),clipFrames=(frames-1)*multiplier+1;$('#ad-duration').textContent=(total?`Montaje: ${total} s · ${Math.ceil(total*fps*multiplier/clipFrames)} escenas aprox.`:'Clip: '+(clipFrames/(fps*multiplier)).toLocaleString('es',{maximumFractionDigits:1})+' s')+' · salida a '+(fps*multiplier)+' fps.';$('#ad-denoise-value').textContent=Number($('#ad-denoise').value).toFixed(2);}
$('#ad-duration-seconds').onchange=updateAdDuration;
$('#ad-mode').onchange=updateAdMode;
$('#ad-frames').onchange=updateAdDuration;
$('#ad-fps').onchange=updateAdDuration;
$('#ad-interpolation').onchange=updateAdDuration;
$('#ad-denoise').oninput=updateAdDuration;
$('#ad-clear-image').onclick=()=>{state.adSource=null;$('#ad-file').value='';$('#ad-reference').hidden=true;$('#ad-upload-label').hidden=false;$('#ad-clear-image').hidden=true;};
function adModelLabel(name){return {'Realistic_Vision_V6.0_NV_B1_fp16.safetensors':'Realistic Vision 6 · fotorrealismo','DreamShaper_8_pruned.safetensors':'DreamShaper 8 · creativo','v1-5-pruned-emaonly-fp16.safetensors':'SD 1.5 · base'}[name]||name;}
async function loadAdStatus(){try{
 const data=await api('animatediff/status');state.adReady=data.ready;state.adDefaultCheckpoint=data.default_checkpoint;
 const current=$('#ad-model').value,signature=JSON.stringify(data.checkpoints);
 if(signature!==state.adCheckpointSignature){state.adCheckpointSignature=signature;$('#ad-model').innerHTML=data.checkpoints.length?data.checkpoints.map(m=>`<option value="${esc(m)}">${esc(adModelLabel(m))}</option>`).join(''):'<option value="">No hay checkpoints SD 1.5 instalados</option>';$('#ad-model').value=data.checkpoints.includes(current)?current:data.default_checkpoint;}
 for(const [id,items,labels] of [['ad-motion-model',data.motion_models||[],{'mm_sd15_v3.safetensors':'AnimateDiff v3','mm_sd15_v2.safetensors':'AnimateDiff v2 · cámara'}],['ad-motion-lora',['',...(data.motion_loras||[])],{'':'Sin LoRA · cámara libre','v2_lora_ZoomOut.ckpt':'Alejar cámara','v2_lora_PanLeft.ckpt':'Desplazar a la izquierda'}]]){
  const select=$('#'+id),key=JSON.stringify(items);if(select.dataset.options!==key){const value=select.value;select.innerHTML=items.map(m=>`<option value="${esc(m)}">${esc(labels[m]||m)}</option>`).join('');if(items.includes(value)&&select.dataset.options)select.value=value;else select.value=id==='ad-motion-model'?data.default_motion_model:data.default_motion_lora||'';select.dataset.options=key;}
 }
 state.adInterpolationReady=data.interpolation_ready;if(!data.interpolation_ready)$('#ad-interpolation').value='1';$('#ad-interpolation').querySelectorAll('option').forEach(o=>o.disabled=o.value!=='1'&&!data.interpolation_ready);const required=data.models.filter(m=>!m.optional),installed=required.filter(m=>m.ready).length;
 $('#ad-model-status').textContent=data.ready?'SD 1.5 + AnimateDiff · Listo':installed<required.length?`Instalando AnimateDiff: ${installed}/${required.length}`:data.node_ready?'Añade un checkpoint SD 1.5 compatible.':'Inicia ComfyUI con AnimateDiff Evolved instalado.';
 updateAdCamera();updateAdDuration();$('#generate-ad').disabled=!data.ready||!!state.adUploading||!!state.adSubmitting;
}catch(e){$('#ad-model-status').textContent=e.message;}}
function updateAdCamera(){const camera=!!$('#ad-motion-lora').value;if(camera)$('#ad-motion-model').value='mm_sd15_v2.safetensors';$('#ad-camera-strength-field').hidden=!camera;$('#ad-camera-strength-value').textContent=Number($('#ad-camera-strength').value).toFixed(2);$('#ad-motion-scale-value').textContent=Number($('#ad-motion-scale').value).toFixed(2);}
$('#ad-motion-lora').onchange=updateAdCamera;
$('#ad-motion-model').onchange=()=>{if($('#ad-motion-model').value!=='mm_sd15_v2.safetensors')$('#ad-motion-lora').value='';updateAdCamera();};
$('#ad-camera-strength').oninput=updateAdCamera;
$('#ad-motion-scale').oninput=updateAdCamera;
function applyAdPeoplePreset(realistic=false){
 const preferred=realistic?'Realistic_Vision_V6.0_NV_B1_fp16.safetensors':'DreamShaper_8_pruned.safetensors';
 const available=Array.from($('#ad-model').options).some(o=>o.value===preferred);if(available)$('#ad-model').value=preferred;else if(state.adDefaultCheckpoint)$('#ad-model').value=state.adDefaultCheckpoint;
 for(const [key,value] of Object.entries({size:'512x320',frames:48,fps:8,steps:24,cfg:6,sampler:'dpmpp_2m',scheduler:'karras','motion-scale':1.15,interpolation:state.adInterpolationReady?3:1}))$('#ad-'+key).value=value;
 const camera=!realistic&&Array.from($('#ad-motion-lora').options).some(o=>o.value==='v2_lora_ZoomOut.ckpt');$('#ad-motion-model').value=camera?'mm_sd15_v2.safetensors':'mm_sd15_v3.safetensors';$('#ad-motion-lora').value=camera?'v2_lora_ZoomOut.ckpt':'';$('#ad-camera-strength').value=0.3;
 $('#ad-negative').value=realistic?'worst quality, low quality, cgi, 3d, cartoon, anime, illustration, extra limbs, fused bodies, bad anatomy, bad hands, blurry, watermark, text':'worst quality, low quality, blurry, deformed anatomy, extra limbs, fused bodies, duplicate person, disfigured face, watermark, text';
 updateAdDuration();updateAdCamera();toast((realistic?'Perfil de realismo':'Perfil de acción')+' aplicado. El prompt se conserva.');
}
$('#ad-people-preset').onclick=()=>applyAdPeoplePreset();
$('#ad-realism-preset').onclick=()=>applyAdPeoplePreset(true);
$('#ad-fight-example').onclick=()=>{$('#ad-prompt').value='Realistic live action martial arts sparring, wide full-body shot of two adult men in a sunlit training gym. A boxer on the left wears red boxing gloves, a black sleeveless shirt and blue shorts. A kung fu practitioner on the right wears a white martial arts uniform and black trousers. The boxer throws one slow straight punch, the martial artist blocks it. Controlled footwork, continuous shot, natural anatomy, cinematic daylight.';$('#ad-people-preset').click();$('#ad-prompt').focus();};

async function loadAdVideos(){const all=await api('renders');const items=all.filter(r=>r.params.backend==='animatediff');state.adRenders=items;updateList('#ad-results',items,r=>`<article class="video-result"><div class="answer-brand">${icon('motion')}AnimateDiff <span class="answer-meta">${r.params.width} × ${r.params.height} · ${videoDuration(r.params).toFixed(1)} s · ${videoFps(r.params)} fps${r.params.batch_count>1?' · '+r.params.batch_index+'/'+r.params.batch_count:''}</span></div><p class="video-hint">${esc(adModelLabel(r.params.model))} · ${r.params.motion_model==='mm_sd15_v2.safetensors'?'v2':'v3'}${r.params.motion_lora?' · '+esc(r.params.motion_lora.includes('ZoomOut')?'cámara: alejar':'cámara: izquierda'):''}${r.params.interpolation>1?' · RIFE '+r.params.interpolation+'×':''}</p>${r.status==='done'?media(r):`<div class="render-status ${r.status==='error'?'error':''}">${r.status==='error'?icon('info'):'<span class="spinner"></span>'}<span>${esc(r.detail)}</span></div>`}<p>${esc(r.prompt)}</p>${actions(r)}</article>`,'<div class="empty-state"><strong>De una idea a una secuencia.</strong>Prepara una nueva creación para empezar.</div>');}
$('#ad-file').onchange=async()=>{const file=$('#ad-file').files[0];if(!file)return;state.adUploading=true;$('#generate-ad').disabled=true;try{const form=new FormData();form.append('image',file);const response=await fetch('/api/animatediff/input',{method:'POST',body:form});const result=await response.json();if(!response.ok)throw Error(result.error||'No se pudo preparar la referencia.');state.adSource={input_image:result.name};$('#ad-reference').src=result.url;$('#ad-reference').hidden=false;$('#ad-upload-label').hidden=true;$('#ad-clear-image').hidden=false;toast('Referencia de AnimateDiff preparada localmente.');}catch(e){toast(e.message);}finally{state.adUploading=false;$('#generate-ad').disabled=!state.adReady;}};
$('#ad-form').onsubmit=async e=>{e.preventDefault();const reference=$('#ad-mode').value==='reference';if(reference&&!state.adSource){toast('Selecciona una imagen o elige Texto a vídeo.');return;}if(state.adUploading||state.adSubmitting)return;state.adSubmitting=true;$('#generate-ad').disabled=true;try{const [width,height]=$('#ad-size').value.split('x').map(Number);const payload={...(reference?state.adSource:{}),count:Number($('#ad-count').value),prompt:$('#ad-prompt').value,model:$('#ad-model').value,width,height};['frames','fps','steps','cfg','seed','denoise'].forEach(k=>payload[k]=Number($('#ad-'+k).value));payload.duration_seconds=Number($('#ad-duration-seconds').value);payload.scene_prompts=$('#ad-scenes').value.split('\n').map(s=>s.trim()).filter(Boolean);payload.negative=$('#ad-negative').value;payload.motion_model=$('#ad-motion-model').value;payload.motion_lora=$('#ad-motion-lora').value;payload.motion_lora_strength=Number($('#ad-camera-strength').value);payload.motion_scale=Number($('#ad-motion-scale').value);payload.interpolation=Number($('#ad-interpolation').value);payload.sampler=$('#ad-sampler').value;payload.scheduler=$('#ad-scheduler').value;const batch=await api('animatediff/generate',payload);await Promise.all([loadAdVideos(),loadChats()]);toast(batch.count===1?'AnimateDiff en cola. Se generará en tu GPU.':batch.count+' vídeos AnimateDiff en cola, con semillas distintas.');}catch(error){toast(error.message);}finally{state.adSubmitting=false;$('#generate-ad').disabled=!state.adReady;}};


function updateList(selector,items,render,empty){
 const parent=$(selector);
 let cache=listCache.get(parent);
 if(!cache){cache=new Map();listCache.set(parent,cache);}
 const wanted=new Set(items.map(item=>item.id));
 for(const [id,entry] of cache){if(!wanted.has(id)){entry.node.remove();cache.delete(id);}}
 if(!items.length){if(parent.dataset.empty!=='true'){parent.innerHTML=empty;parent.dataset.empty='true';}return;}
 if(parent.dataset.empty==='true'||!cache.size){parent.replaceChildren();delete parent.dataset.empty;}
 for(let index=0;index<items.length;index++){
  const item=items[index],signature=JSON.stringify(item);
  let entry=cache.get(item.id);
  if(!entry||entry.signature!==signature){
   const template=document.createElement('template');template.innerHTML=render(item);
   const node=template.content.firstElementChild;
   if(entry)entry.node.replaceWith(node);
   entry={node,signature};cache.set(item.id,entry);
  }
  const current=parent.children[index];
  if(current!==entry.node)parent.insertBefore(entry.node,current||null);
 }
}
function updateVideoCount(){for(const [input,label,base] of [['video-count','video-generate-label','Generar vídeo local'],['ad-count','ad-generate-label','Generar con AnimateDiff']]){const n=Number($('#'+input).value);$('#'+label).textContent=n>1?'Generar '+n+' vídeos':base;}}
$('#video-count').onchange=updateVideoCount;
$('#ad-count').onchange=updateVideoCount;

if(['video','gallery'].includes(new URLSearchParams(location.search).get('view')))setView(new URLSearchParams(location.search).get('view'));

async function loadQueueStatus(){
 try{
  const q=await api('queue/status');state.generationQueue=q;updateGpuControls(q);
  const pending=q.queued+q.paused_jobs+(q.failed_jobs||0);
  $('#queue-summary').textContent=q.stopping?'Deteniendo generación…':q.paused?`Cola pausada · ${pending} pendientes${q.active_id?' · la actual sigue generándose':''}`:q.active_id?`Generando · ${pending} en cola`:`Cola lista · ${pending} pendientes`;
  $('#stop-generation').disabled=!q.active_id||q.stopping;
  $('#pause-queue').disabled=q.paused;
  $('#resume-queue').disabled=!q.paused||q.stopping;
  $('#queue-error').hidden=!q.error;$('#queue-error').textContent=q.error||'';
 }catch(e){$('#queue-summary').textContent='Controles de cola pendientes de conexión';for(const id of ['stop-generation','pause-queue','resume-queue'])$('#'+id).disabled=true;}
}
for(const [id,action,message] of [['stop-generation','stop','Deteniendo la actual y pausando la cola.'],['pause-queue','pause','Cola pausada. La generación actual puede terminar.'],['resume-queue','resume','Continuando los trabajos pendientes.']]){
 $('#'+id).onclick=async()=>{const button=$('#'+id);button.disabled=true;try{await api('queue/'+action,{});await Promise.all([loadQueueStatus(),loadConversation(),loadVideos(),loadMeshes(),loadAdVideos()]);toast(message);}catch(e){toast(e.message);await loadQueueStatus();}};
}

function updateGpuControls(q){
 if(!$('#release-gpu-after')||!$('#release-gpu-now')||!$('#gpu-memory-info'))return;
 const g=q.gpu;$('#release-gpu-after').disabled=!g||g.cleaning;$('#release-gpu-now').disabled=!g||!!q.active_id||g.cleaning;
 if(!g){$('#gpu-memory-info').textContent='Reinicia Studio para activar la limpieza GPU.';return;}
 $('#release-gpu-after').checked=g.enabled;
 $('#gpu-memory-info').textContent=g.cleaning?'Liberando modelos y caché GPU…':g.warning||(!g.enabled?'Limpieza automática desactivada.':g.last_report?'Última limpieza: '+new Date(g.last_report.time*1000).toLocaleTimeString('es')+'.':'Activa antes y después de generar. El modelo puede tardar más en cargar.');
}
if($('#release-gpu-after'))$('#release-gpu-after').onchange=async()=>{try{await api('gpu/settings',{enabled:$('#release-gpu-after').checked});await loadQueueStatus();}catch(e){toast(e.message);await loadQueueStatus();}};
if($('#release-gpu-now'))$('#release-gpu-now').onclick=async()=>{const button=$('#release-gpu-now');button.disabled=true;try{await api('gpu/release',{});await loadQueueStatus();toast('Limpieza solicitada a los motores inactivos.');}catch(e){toast(e.message);}finally{await loadQueueStatus();}};

function galleryEngine(r){return {comfy:'ComfyUI',automatic:'A1111 / Forge',qwen:'Qwen'}[r.params?.engine]||r.params?.engine||'Sin motor';}
function collectibleNumber(p){return p.numero_pokedex||((p.numero??p.batch_index)!=null?'#'+String(p.numero??p.batch_index).padStart(3,'0'):'');}
function compactGalleryCard(r){
 const p=r.params||{},title=p.item_name||r.prompt?.slice(0,52)||'Sin título',number=collectibleNumber(p);
 return `<article class="gallery-item collectible-card"><div class="sticker-frame">${number?`<span class="sticker-number">${esc(number)}</span>`:''}${p.kind==='video'||p.kind==='mesh'?media(r,true):`<button type="button" class="sticker-open" data-describe-render="${esc(r.id)}" aria-label="Abrir descripción de ${esc(title)}">${media(r,true)}</button>`}</div><div class="collectible-caption"><strong title="${esc(title)}">${esc(title)}</strong><span>${esc(galleryEngine(r))}</span><button type="button" class="collectible-description" data-describe-render="${esc(r.id)}" aria-label="Ver descripción de ${esc(title)}">${icon('info')}</button></div></article>`;
}
function albumCover(b){
 const pictures=b.items.filter(i=>i.status==='done'&&!i.deleted&&i.image).slice(0,4);
 return `<button type="button" class="album-cover" data-open-album="${esc(b.id)}"><span class="album-cover-art">${Array.from({length:4},(_,i)=>pictures[i]?`<img src="${esc(pictures[i].image)}" alt="" loading="lazy">`:'<span class="album-cover-empty">✦</span>').join('')}</span><span class="album-cover-label"><strong>${esc(b.name)}</strong><span>${pictures.length?b.items.filter(i=>i.status==='done'&&!i.deleted).length:0} de ${b.total} figuritas</span></span></button>`;
}
function renderGalleryCollections(){
 const batches=state.galleryBatches||[],done=(state.gallery||[]).filter(r=>r.status==='done');
 state.galleryMode ||= batches.length?'albums':'all';
 const selected=batches.find(b=>b.id===state.selectedAlbum);
 const toolbar=$('#gallery-toolbar'),covers=$('#gallery-albums'),grid=$('#gallery');
 if(!toolbar||!covers)return;
 const toolbarHtml=`<div class="gallery-tabs" role="group" aria-label="Vista de la colección"><button type="button" data-gallery-mode="albums" aria-pressed="${state.galleryMode==='albums'}">Álbumes JSON <span>${batches.length}</span></button><button type="button" data-gallery-mode="all" aria-pressed="${state.galleryMode==='all'}">Todos los resultados <span>${done.length}</span></button></div>${state.galleryMode==='albums'&&selected?`<div class="album-heading"><button type="button" class="secondary-button" data-gallery-mode="albums">← Todos los álbumes</button><div><h2>${esc(selected.name)}</h2><p>${selected.items.filter(i=>i.status==='done'&&!i.deleted).length} / ${selected.total} figuritas · orden del archivo JSON</p></div></div>`:''}`;
 if(toolbar.dataset.content!==toolbarHtml){toolbar.innerHTML=toolbarHtml;toolbar.dataset.content=toolbarHtml;}
 covers.hidden=state.galleryMode!=='albums'||!!selected;
 grid.hidden=state.galleryMode==='albums'&&!selected;
 if(state.galleryMode==='albums'&&!selected){
  updateList('#gallery-albums',batches,albumCover,'<div class="empty-state"><strong>Tu primer álbum empieza con un JSON.</strong>Los lotes importados aparecen aquí, con una figurita por imagen.<button type="button" class="secondary-button" data-view="batches">Importar un lote</button></div>');
  return;
 }
 if(state.galleryMode==='albums'&&selected){
  const byId=new Map((state.gallery||[]).map(r=>[r.id,r]));
  const entries=selected.items.map(item=>({...item,render:byId.get(item.id)}));
  updateList('#gallery',entries,item=>{
   if(item.status==='done'&&!item.deleted&&item.render?.image)return compactGalleryCard(item.render);
   const label=item.deleted?'En papelera':{running:'Generando',error:'Pendiente de reintento',paused:'En pausa',queued:'Por generar'}[item.status]||'Por generar';
   return `<article class="gallery-item collectible-card collectible-missing"><div class="sticker-frame"><span class="sticker-number">${esc(collectibleNumber(item)||String(item.index).padStart(3,'0'))}</span><span class="sticker-placeholder"><span>✦</span>${esc(label)}</span></div><div class="collectible-caption"><strong>${esc(item.name)}</strong><span>Falta en el álbum</span></div></article>`;
  },'');
 }else{
  updateList('#gallery',done,compactGalleryCard,`<div class="empty-state">${icon('grid')}<strong>Tu colección está por empezar.</strong><button type="button" class="generate-button" id="first-image">Crear mi primera imagen</button></div>`);
 }
}
function renderImageDescription(r){
 const p=r.params||{},title=p.item_name||({'video':'Vídeo','mesh':'Modelo 3D'}[p.kind]||'Imagen generada'),number=collectibleNumber(p);
 const album=(state.galleryBatches||[]).find(b=>b.id===p.image_batch_id);
 const fields=[['Motor',p.engine==='qwen'?'Qwen · stable-diffusion.cpp':names[p.engine]||p.engine||'No registrado'],['Modelo',p.model||'No registrado'],['VAE',p.vae||'Del modelo'],['LoRAs',p.loras?.map(l=>`${l.name} (modelo ${l.strength_model}, CLIP ${l.strength_clip})`).join(' · ')||'Sin LoRAs'],['Sampler',p.sampler||(p.engine==='qwen'?'Euler':'Predeterminado')],['Scheduler',p.scheduler||'Del flujo'],['Transformación',p.input_image?p.denoise:null],['Resolución',`${p.width} × ${p.height}`],['Pasos',p.steps],['CFG',p.cfg],['Semilla',p.seed],['Álbum',album?.name],['Posición',p.image_batch_id?`${p.batch_index} / ${p.batch_count}`:null],['Número',p.numero],['Pokédex',p.numero_pokedex],['Creada',r.created?new Date(r.created*1000).toLocaleString('es'):null]];
 return `<div class="image-description"><div class="description-eyebrow">${esc(number||'TU CREACIÓN')}</div><h2>${esc(title)}</h2><h3>Descripción · prompt</h3><p class="description-prompt">${esc(r.prompt)}</p><h3>Prompt negativo</h3><p class="description-prompt">${esc(p.negative||'Sin prompt negativo')}</p><dl class="image-facts">${fields.filter(([,value])=>value!=null).map(([key,value])=>`<div><dt>${esc(key)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl>${actions(r)}<details class="description-parameters"><summary>Todos los parámetros</summary><pre>${esc(JSON.stringify(p,null,2))}</pre></details></div>`;
}
function openRenderDescription(r){
 if(!r)return;
 const visual=$('#description-media');
 $('#full-image').hidden=['video','mesh'].includes(r.params.kind);
 if(visual){visual.hidden=!$('#full-image').hidden;visual.innerHTML=visual.hidden?'':media(r,true);}
 $('#full-image').src=$('#full-image').hidden?'':r.image;$('#full-image').alt=r.prompt;
 $('#image-meta').innerHTML=renderImageDescription(r);
 if(!$('#image-dialog').open)$('#image-dialog').showModal();
}

document.addEventListener('click',event=>{
 const button=event.target.closest('[data-open-album],[data-gallery-mode]');if(!button)return;
 if(button.dataset.openAlbum){state.galleryMode='albums';state.selectedAlbum=button.dataset.openAlbum;}
 else{state.galleryMode=button.dataset.galleryMode;state.selectedAlbum=null;}
 if(state.view!=='gallery')setView('gallery');
 renderGalleryCollections();
});
$('#image-dialog').addEventListener('close',()=>{if($('#description-media'))$('#description-media').replaceChildren();$('#full-image').removeAttribute('src');});

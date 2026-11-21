let queueJobs=[],queueGroups=[],queueSelected=new Set(),queueExpanded=new Set(),queueRequest=0,queueEditing=null;
const queueLabels={queued:'En cola',running:'Generando',paused:'En pausa',error:'Con error',cancelled:'Cancelado',done:'Finalizando'};
const queueKind={image:'Imagen',video:'Vídeo',mesh:'3D'};
function queueThumb(job){return job.preview?`<img src="${esc(job.preview)}" loading="lazy" alt="Referencia de ${esc(job.title)}">`:`<span class="queue-placeholder" aria-label="Sin imagen de referencia">${icon(job.kind==='video'?'video':job.kind==='mesh'?'cube':'grid')}</span>`;}
function queueRow(job){
 const pending=['queued','paused','error'].includes(job.status)&&!job.active,cancelled=job.status==='cancelled';
 return `<article class="queue-job ${job.active?'queue-job-active':''}"><input class="queue-select" type="checkbox" data-queue-select="${esc(job.id)}" ${queueSelected.has(job.id)?'checked':''} ${job.active?'disabled':''} aria-label="Seleccionar ${esc(job.title)}"><div class="queue-thumb">${queueThumb(job)}</div><div class="queue-job-copy"><strong>${esc(job.title)}</strong><span>${job.position?'#'+job.position+' · ':''}${queueKind[job.kind]||job.kind} · ${queueLabels[job.status]||job.status}${job.cancel_requested&&job.active?' · cancelando…':''} · prioridad ${job.priority}</span>${job.active||job.status==='error'?`<small>${esc(job.detail)}</small>`:''}</div><div class="queue-job-actions">${!job.active?`<button type="button" class="secondary-button" data-queue-edit="${esc(job.id)}">Editar</button>`:''}${pending?`<button type="button" class="secondary-button" data-queue-move="first" data-queue-id="${esc(job.id)}" title="Poner primero entre los pendientes">Primero</button><button type="button" class="icon-button" data-queue-move="up" data-queue-id="${esc(job.id)}" aria-label="Subir ${esc(job.title)}">↑</button><button type="button" class="icon-button" data-queue-move="down" data-queue-id="${esc(job.id)}" aria-label="Bajar ${esc(job.title)}">↓</button>`:''}${!job.active&&['paused','error','cancelled'].includes(job.status)?`<button type="button" class="secondary-button" data-queue-requeue="${esc(job.id)}">${cancelled?'Volver a encolar':'Reintentar'}</button>`:''}${job.status!=='done'&&!cancelled?`<button type="button" class="danger-button" data-queue-cancel="${esc(job.id)}" ${job.cancel_requested?'disabled':''}>${job.active?'Cancelar activo':'Cancelar'}</button>`:''}</div></article>`;
}
function queueGroup(group){
 const pending=group.jobs.filter(j=>['queued','paused','error'].includes(j.status)&&!j.active),active=group.jobs.some(j=>j.active);
 return `<details class="queue-group" data-queue-group="${esc(group.id)}" ${queueExpanded.has(group.id)?'open':''}><summary><span class="queue-group-thumbs">${group.jobs.slice(0,3).map(j=>queueThumb(j)).join('')}</span><span class="queue-group-name"><strong>${esc(group.title)}</strong><span>${group.jobs.length} trabajos${active?' · uno activo':''} · ${pending.length} pendientes</span></span><span class="queue-expand-label">Desplegar</span></summary><div class="queue-group-body"><div class="queue-group-tools"><button type="button" class="secondary-button" data-queue-select-group="${esc(group.id)}">Seleccionar pendientes</button><button type="button" class="danger-button" data-queue-cancel-group="${esc(group.id)}" ${pending.length?'':'disabled'}>Cancelar pendientes del grupo</button>${group.batchId?`<button type="button" class="secondary-button" data-open-album="${esc(group.batchId)}">Ver álbum</button><button type="button" class="secondary-button" data-rename-album="${esc(group.batchId)}">Cambiar nombre</button>`:''}</div>${group.jobs.map(queueRow).join('')}</div></details>`;
}
function renderQueueBoard(){
 const kind=$('#queue-kind').value,showCancelled=$('#queue-show-cancelled').checked;
 const jobs=queueJobs.filter(j=>(kind==='all'||j.kind===kind)&&(showCancelled||j.status!=='cancelled'));
 const valid=new Set(queueJobs.filter(j=>!j.active&&j.status!=='done').map(j=>j.id));queueSelected=new Set([...queueSelected].filter(id=>valid.has(id)));
 let position=0;for(const job of queueJobs)job.position=!job.active&&job.status==='queued'?++position:null;
 const active=queueJobs.find(j=>j.active);
 $('#queue-active').innerHTML=active?`<div class="queue-active-heading"><span class="status-dot"></span>En ejecución · ${queueKind[active.kind]||active.kind}</div>${queueRow(active)}`:'<p class="queue-idle">Sin generación activa. Los pendientes siguen el orden y la prioridad guardados.</p>';
 const groups=new Map();
 for(const job of jobs){if(!groups.has(job.group_id))groups.set(job.group_id,{id:job.group_id,title:job.group_title,batchId:job.batch_id,jobs:[]});groups.get(job.group_id).jobs.push(job);}
 queueGroups=[...groups.values()];
 updateList('#queue-groups',queueGroups,queueGroup,'<div class="empty-state"><strong>No hay trabajos en esta vista.</strong>Las imágenes y los vídeos en cola aparecerán aquí.</div>');
 for(const box of $('#queue-groups').querySelectorAll('[data-queue-select]'))box.checked=queueSelected.has(box.dataset.queueSelect);
 for(const details of $('#queue-groups').querySelectorAll('[data-queue-group]'))details.open=queueExpanded.has(details.dataset.queueGroup);
 $('#queue-board-summary').textContent=`${queueJobs.filter(j=>j.active).length} activo · ${queueJobs.filter(j=>j.status==='queued').length} en cola · ${queueJobs.filter(j=>j.status==='paused').length} pausados · ${queueJobs.filter(j=>j.status==='error').length} con error`;
 $('#queue-selection-count').textContent=`${queueSelected.size} seleccionados`;
 for(const id of ['queue-cancel-selected','queue-apply-priority','queue-requeue-selected'])$('#'+id).disabled=!queueSelected.size;
}
async function loadQueueJobs(){
 const id=++queueRequest;
 try{const data=await api('queue/jobs');if(id!==queueRequest)return;queueJobs=data.jobs;let position=0;for(const job of queueJobs)job.position=!job.active&&job.status==='queued'?++position:0;const editableIds=new Set(queueJobs.filter(j=>!j.active&&j.status!=='running'&&j.status!=='done').map(j=>j.id));queueSelected=new Set([...queueSelected].filter(id=>editableIds.has(id)));$('#queue-board-error').hidden=true;renderQueueBoard();}
 catch(e){$('#queue-board-error').hidden=false;$('#queue-board-error').textContent=e.message;}
}
async function queueCommand(path,body){await api('queue/'+path,body);await Promise.all([loadQueueJobs(),loadQueueStatus()]);}
$('#queue-groups').addEventListener('toggle',event=>{
 const d=event.target;if(!d.matches?.('[data-queue-group]')||!d.isConnected)return;
 if(d.open)queueExpanded.add(d.dataset.queueGroup);else queueExpanded.delete(d.dataset.queueGroup);
},true);
document.addEventListener('change',event=>{
 const checkbox=event.target.closest('[data-queue-select]');if(!checkbox)return;
 if(checkbox.checked)queueSelected.add(checkbox.dataset.queueSelect);else queueSelected.delete(checkbox.dataset.queueSelect);renderQueueBoard();
});
for(const id of ['queue-kind','queue-show-cancelled'])$('#'+id).onchange=()=>{queueSelected.clear();renderQueueBoard();};
$('#queue-expand-all').onclick=()=>{queueGroups.forEach(g=>queueExpanded.add(g.id));renderQueueBoard();};
$('#queue-collapse-all').onclick=()=>{queueExpanded.clear();renderQueueBoard();};
$('#queue-clear-selected').onclick=()=>{queueSelected.clear();renderQueueBoard();};
$('#queue-cancel-selected').onclick=async()=>{try{await queueCommand('cancel',{ids:[...queueSelected],pending_only:true});queueSelected.clear();renderQueueBoard();toast('Cancelación solicitada. Los cancelados no se reanudan automáticamente.');}catch(e){toast(e.message);}};
$('#queue-requeue-selected').onclick=async()=>{try{await queueCommand('requeue',{ids:[...queueSelected]});queueSelected.clear();renderQueueBoard();toast('Trabajos devueltos a la cola.');}catch(e){toast(e.message);}};
$('#queue-apply-priority').onclick=async()=>{try{await queueCommand('priority',{ids:[...queueSelected],priority:Number($('#queue-priority').value)});toast('Prioridad guardada para los pendientes.');}catch(e){toast(e.message);}};
document.addEventListener('click',async event=>{
 const b=event.target.closest('[data-queue-edit],[data-queue-cancel],[data-queue-requeue],[data-queue-move],[data-queue-select-group],[data-queue-cancel-group]');if(!b)return;
 b.disabled=true;
 try{
  if(b.dataset.queueCancel){await queueCommand('cancel',{ids:[b.dataset.queueCancel]});toast('Cancelación solicitada.');}
  if(b.dataset.queueRequeue){await queueCommand('requeue',{ids:[b.dataset.queueRequeue]});toast('Trabajo devuelto a la cola.');}
  if(b.dataset.queueMove)await queueCommand('priority',{ids:[b.dataset.queueId],move:b.dataset.queueMove});
  if(b.dataset.queueSelectGroup||b.dataset.queueCancelGroup){
   const group=queueGroups.find(g=>g.id===(b.dataset.queueSelectGroup||b.dataset.queueCancelGroup));
   const ids=group?.jobs.filter(j=>!j.active&&['queued','paused','error'].includes(j.status)).map(j=>j.id)||[];
   if(b.dataset.queueSelectGroup){ids.forEach(id=>queueSelected.add(id));renderQueueBoard();}
   else if(ids.length){await queueCommand('cancel',{ids,pending_only:true});toast('Pendientes del grupo cancelados; el activo sigue su curso.');}
  }
  if(b.dataset.queueEdit){
   const job=queueJobs.find(j=>j.id===b.dataset.queueEdit);if(!job||job.active)throw Error('El trabajo activo no se puede editar.');
   await api('queue/pause',{});await loadQueueStatus();
   if(job.kind==='image'){await editQueuedImage(job);return;}
   openQueueEditor(job);
  }
 }catch(e){toast(e.message);}finally{b.disabled=false;}
});
function openQueueEditor(job){
 queueEditing=job;const p=job.params,video=job.kind==='video',animated=p.backend==='animatediff';
 $('#queue-edit-title').value=job.title;$('#queue-edit-prompt').value=job.prompt;$('#queue-edit-negative').value=p.negative||'';
 $('#queue-edit-model').textContent=`${p.model} · se conserva la arquitectura del trabajo`;
 for(const key of ['width','height','steps','cfg','seed','frames','fps','shift','denoise','interpolation','faces'])$('#queue-edit-'+key).value=p[key]??({shift:5,denoise:1,interpolation:1,faces:100000}[key]||1);
 for(const key of ['width','height','cfg','frames','fps','shift','denoise','interpolation','duration','scenes','negative'])$('#queue-edit-'+key).closest('label').hidden=!video||((key==='shift')&&animated)||((key==='denoise')&&!animated);
 $('#queue-edit-faces').closest('label').hidden=video;
 $('#queue-edit-duration').value=p.duration_seconds||0;$('#queue-edit-scenes').value=(p.scene_prompts||[]).join('\n');
 for(const key of ['width','height']){const el=$('#queue-edit-'+key);el.min=animated?128:256;el.max=animated?768:1280;el.step=animated?8:32;}
 $('#queue-edit-steps').min=4;$('#queue-edit-steps').max=video?(animated?50:60):30;
 $('#queue-edit-cfg').min=1;$('#queue-edit-cfg').max=animated?20:8;
 $('#queue-edit-frames').min=animated?4:9;$('#queue-edit-frames').max=animated?64:121;$('#queue-edit-frames').step=animated?1:8;
 for(const field of $('#queue-edit-form').querySelectorAll('input,textarea'))field.disabled=!!field.closest('label')?.hidden;
 $('#queue-edit-fps').disabled=!animated;
 $('#queue-edit-interpolation').max=animated?3:2;
 $('#queue-edit-dialog').showModal();
}
$('#queue-edit-close').onclick=()=>$('#queue-edit-dialog').close();
$('#queue-edit-form').onsubmit=async event=>{
 event.preventDefault();if(!queueEditing)return;
 const job=queueEditing,p=job.params,params={};
 const keys=job.kind==='mesh'?['steps','seed','faces']:['width','height','steps','cfg','seed','frames','fps','interpolation'];
 if(job.kind==='video'){if(p.backend==='animatediff')keys.push('denoise');else keys.push('shift');params.negative=$('#queue-edit-negative').value;params.duration_seconds=Number($('#queue-edit-duration').value);params.scene_prompts=$('#queue-edit-scenes').value.split('\n').map(s=>s.trim()).filter(Boolean);}
 for(const key of keys)params[key]=Number($('#queue-edit-'+key).value);
 const button=$('#queue-edit-save');button.disabled=true;
 try{const r=await api('queue/jobs/'+job.id+'/edit',{title:$('#queue-edit-title').value,prompt:$('#queue-edit-prompt').value,params});$('#queue-edit-dialog').close();await loadQueueJobs();toast(r.archived_scenes?'Cambios guardados. Las escenas anteriores se archivaron; se recalculará el montaje.':'Cambios guardados. La cola permanece pausada; pulsa Continuar cuando quieras.');}
 catch(e){toast(e.message);}finally{button.disabled=false;}
};
setInterval(()=>{if(state.view==='queue')loadQueueJobs();},2000);
if(new URLSearchParams(location.search).get('view')==='queue')setView('queue');

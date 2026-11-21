const batchExample = [
 {numero:25,numero_pokedex:'#025',nombre:'Pikachu',prompt:'A real-life Pikachu imagined as a living wild animal, small pika-like rodent, dense yellow fur, long black-tipped ears, red cheek pouches, wildlife photography, natural forest light',negative_prompt:'cartoon, anime, 3d render, cgi, plastic, toy'},
 {numero:26,numero_pokedex:'#026',nombre:'Raichu',prompt:'A real-life Raichu imagined as a living wild animal, orange brown fur, pale belly, long slender tail, wildlife photography, natural forest light',negative_prompt:'cartoon, anime, 3d render, cgi, plastic, toy'}];
let selectedImageBatch = null, selectedImageBatchFilename='';
$('#batch-example').onclick=()=>{
 const url=URL.createObjectURL(new Blob([JSON.stringify(batchExample,null,2)],{type:'application/json'}));
 const a=document.createElement('a');a.href=url;a.download='lote-ejemplo.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$('#batch-file').onchange=async()=>{
 selectedImageBatch=null;selectedImageBatchFilename='';$('#batch-import').disabled=true;$('#batch-preview').textContent='';
 try{
  const file=$('#batch-file').files[0];if(!file)return;
  if(file.size>2*1024*1024)throw Error('El JSON no puede superar 2 MB.');
  const data=JSON.parse((await file.text()).replace(/^\uFEFF/,''));
  const entries=Array.isArray(data)?data:Array.isArray(data?.prompts)?data.prompts:typeof data?.prompt==='string'?[data]:null;
  if(!entries?.length||entries.length>1000)throw Error('Incluye una imagen, una lista de imágenes o un objeto con entre 1 y 1000 prompts.');
  selectedImageBatch=data;selectedImageBatchFilename=file.name;
  $('#batch-preview').textContent=`${file.name} · ${entries.length} imágenes, en el orden del archivo.\n`+entries.slice(0,10).map((item,i)=>`${i+1}. ${typeof item==='string'?'Imagen '+(i+1):[item?.numero_pokedex,item?.name||item?.nombre||'Imagen '+(i+1)].filter(Boolean).join(' · ')}`).join('\n')+(entries.length>10?'\n…':'');
  $('#batch-import').disabled=false;
 }catch(e){$('#batch-preview').textContent=e.message;}
};
$('#batch-import').onclick=async()=>{
 if(!selectedImageBatch)return;
 const button=$('#batch-import');button.disabled=true;
 try{
  const settings=readBatchControls();
  const result=await api('image-batches',{document:selectedImageBatch,source_filename:selectedImageBatchFilename,settings,prefer_ui_settings:!$('#batch-json-settings').checked});
  await Promise.all([loadImageBatches(),loadChats(),loadQueueStatus()]);
  toast(result.existing?'Este lote ya está guardado. Usa Continuar para retomar los pendientes.':`${result.count} imágenes guardadas en orden. La cola conserva su estado actual.`);
 }catch(e){toast(e.message);}finally{button.disabled=false;}
};
const batchStatusLabels={queued:'En cola',running:'Generando',paused:'Detenida',error:'Error · reintentar al continuar',done:'Terminada',cancelled:'Cancelada'};
async function loadImageBatches(){
 try{
  const batches=await api('image-batches');state.galleryBatches=batches;state.batchListExpanded ||= new Set();
  updateList('#image-batch-list',batches,b=>{
   const pending=b.pending??b.items.filter(i=>['queued','paused','error'].includes(i.status)).length;
   const covers=b.items.filter(i=>i.status==='done'&&!i.deleted&&i.image).slice(0,3);
   return `<details class="image-batch batch-collapsible" data-batch-fold="${esc(b.id)}" ${state.batchListExpanded.has(b.id)?'open':''}><summary><span class="batch-summary-thumbs">${covers.length?covers.map(i=>`<img src="${esc(i.image)}" alt="" loading="lazy">`).join(''):'<span>✦</span>'}</span><span class="batch-summary-title"><strong>${esc(b.name)}</strong><span>${b.done} / ${b.total} terminadas · ${pending} pendientes${b.cancelled?' · '+b.cancelled+' canceladas':''}</span></span></summary><div class="batch-collapsible-body"><div class="batch-list-actions"><button class="secondary-button" data-chat="${esc(b.chat_id)}">Ver conversación</button><button type="button" class="secondary-button" data-open-album="${esc(b.id)}">Ver álbum</button><button type="button" class="secondary-button" data-rename-album="${esc(b.id)}">Cambiar nombre</button><button type="button" class="secondary-button" data-view="queue">Gestionar cola</button><button type="button" class="secondary-button" data-edit-batch-settings="${esc(b.id)}" ${pending?'':'disabled'}>Editar ajustes pendientes</button><button type="button" class="generate-button" data-resume-batch="${esc(b.id)}" ${pending?'':'disabled'}>Retomar · ${pending} pendientes</button></div><div class="batch-compact-items">${b.items.map(item=>`<div class="batch-compact-item">${item.image&&!item.deleted?`<img src="${esc(item.image)}" alt="" loading="lazy" data-image="${esc(item.id)}">`:`<span class="batch-number-placeholder">${esc(item.numero_pokedex||String(item.index).padStart(3,'0'))}</span>`}<div><strong>${esc(item.name)}</strong><span>${esc(batchStatusLabels[item.status]||item.status)}${item.deleted?' · en papelera':''}</span></div></div>`).join('')}</div></div></details>`;
  },'<p>Aún no has importado ningún lote JSON.</p>');
  for(const d of $('#image-batch-list').querySelectorAll('[data-batch-fold]'))d.open=state.batchListExpanded.has(d.dataset.batchFold);
 }catch(e){$('#image-batch-list').textContent=e.message;}
}
$('#image-batch-list').addEventListener('toggle',event=>{const d=event.target;if(!d.matches?.('[data-batch-fold]')||!d.isConnected)return;state.batchListExpanded ||= new Set();if(d.open)state.batchListExpanded.add(d.dataset.batchFold);else state.batchListExpanded.delete(d.dataset.batchFold);},true);
setInterval(()=>{if(state.view==='batches')loadImageBatches();},3000);

document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-resume-batch]');if(!button)return;
 button.disabled=true;
 try{
  await api('queue/resume',{});
  await Promise.all([loadImageBatches(),loadQueueStatus()]);
  toast('Cola reanudada: se reintenta la primera imagen pendiente y se conservan las terminadas.');
 }catch(e){toast(e.message);}finally{button.disabled=false;}
});

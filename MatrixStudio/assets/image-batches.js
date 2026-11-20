const batchExample = [
 {numero:25,numero_pokedex:'#025',nombre:'Pikachu',prompt:'A real-life Pikachu imagined as a living wild animal, small pika-like rodent, dense yellow fur, long black-tipped ears, red cheek pouches, wildlife photography, natural forest light',negative_prompt:'cartoon, anime, 3d render, cgi, plastic, toy'},
 {numero:26,numero_pokedex:'#026',nombre:'Raichu',prompt:'A real-life Raichu imagined as a living wild animal, orange brown fur, pale belly, long slender tail, wildlife photography, natural forest light',negative_prompt:'cartoon, anime, 3d render, cgi, plastic, toy'}];
let selectedImageBatch = null;
$('#batch-example').onclick=()=>{
 const url=URL.createObjectURL(new Blob([JSON.stringify(batchExample,null,2)],{type:'application/json'}));
 const a=document.createElement('a');a.href=url;a.download='lote-ejemplo.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$('#batch-file').onchange=async()=>{
 selectedImageBatch=null;$('#batch-import').disabled=true;$('#batch-preview').textContent='';
 try{
  const file=$('#batch-file').files[0];if(!file)return;
  if(file.size>2*1024*1024)throw Error('El JSON no puede superar 2 MB.');
  const data=JSON.parse((await file.text()).replace(/^\uFEFF/,''));
  const entries=Array.isArray(data)?data:Array.isArray(data?.prompts)?data.prompts:typeof data?.prompt==='string'?[data]:null;
  if(!entries?.length||entries.length>1000)throw Error('Incluye una imagen, una lista de imágenes o un objeto con entre 1 y 1000 prompts.');
  selectedImageBatch=data;
  $('#batch-preview').textContent=`${Array.isArray(data)?'Lote JSON':data.name||data.nombre||'Lote JSON'} · ${entries.length} imágenes, en el orden del archivo.\n`+entries.slice(0,10).map((item,i)=>`${i+1}. ${typeof item==='string'?'Imagen '+(i+1):[item?.numero_pokedex,item?.name||item?.nombre||'Imagen '+(i+1)].filter(Boolean).join(' · ')}`).join('\n')+(entries.length>10?'\n…':'');
  $('#batch-import').disabled=false;
 }catch(e){$('#batch-preview').textContent=e.message;}
};
$('#batch-import').onclick=async()=>{
 if(!selectedImageBatch)return;
 const button=$('#batch-import');button.disabled=true;
 try{
  const [width,height]=$('#size').value.split('x').map(Number);
  const settings={engine:$('#engine').value,model:$('#model').value,width,height,steps:Number($('#steps').value),cfg:Number($('#cfg').value),seed:Number($('#seed').value),negative:$('#negative').value,...selectedImageBatch.settings};
  const result=await api('image-batches',{document:selectedImageBatch,settings});
  await Promise.all([loadImageBatches(),loadChats(),loadQueueStatus()]);
  toast(result.existing?'Este lote ya está guardado. Usa Continuar para retomar los pendientes.':`${result.count} imágenes guardadas en orden. La cola conserva su estado actual.`);
 }catch(e){toast(e.message);}finally{button.disabled=false;}
};
const batchStatusLabels={queued:'En cola',running:'Generando',paused:'Detenida',error:'Error · reintentar al continuar',done:'Terminada'};
async function loadImageBatches(){
 try{
  const batches=await api('image-batches');
  updateList('#image-batch-list',batches,b=>`<article class="image-batch"><div class="inspiration-heading"><h2>${esc(b.name)}</h2><span>${b.done} / ${b.total} terminadas</span></div><button class="secondary-button" data-chat="${esc(b.chat_id)}">Ver imágenes del lote</button><ol>${b.items.map(item=>`<li><strong>${esc([item.numero_pokedex,item.name].filter(Boolean).join(' · '))}</strong><span class="batch-item-status">${esc(batchStatusLabels[item.status]||item.status)}${item.deleted?' · en papelera':''}</span>${item.status==='error'?`<p class="error">${esc(item.detail)}</p>`:''}</li>`).join('')}</ol></article>`, '<p>Aún no has importado ningún lote JSON.</p>');
 }catch(e){$('#image-batch-list').textContent=e.message;}
}
setInterval(()=>{if(state.view==='batches')loadImageBatches();},3000);

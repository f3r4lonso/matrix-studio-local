let batchControlOptions=null,batchControlRequest=0,batchLoraSelection=[],batchReference='',editingBatchId=null;
const batchValue=id=>$('#batch-'+id).value;
function batchOption(value,label,disabled=false){return `<option value="${esc(value)}" ${disabled?'disabled':''}>${esc(label)}</option>`;}
function batchArchitecture(){return batchControlOptions?.models.find(m=>m.name===batchValue('model'))?.architecture||'unknown';}
function refreshBatchAssetChoices(){
 const o=batchControlOptions;if(!o)return;
 const arch=batchArchitecture(),qwen=o.engine==='qwen',previous=batchValue('vae');
 $('#batch-vae').innerHTML=batchOption('','VAE del modelo / automático')+o.vaes.map(v=>batchOption(v.name,`${v.name} · ${v.architecture}`,!['sd15','sdxl'].includes(arch)||v.architecture!==arch)).join('');
 if([...$('#batch-vae').options].some(v=>v.value===previous&&!v.disabled))$('#batch-vae').value=previous;
 $('#batch-vae').disabled=qwen;
 $('#batch-lora-choice').innerHTML=batchOption('','Selecciona una LoRA')+o.loras.map(l=>batchOption(l.name,`${l.name} · ${l.architecture}`,!['sd15','sdxl'].includes(arch)||l.architecture!==arch)).join('');
 $('#batch-lora-choice').disabled=qwen;$('#batch-add-lora').disabled=qwen;
 batchLoraSelection=batchLoraSelection.filter(l=>o.loras.some(v=>v.name===l.name&&v.architecture===arch));
 $('#batch-file-reference').disabled=!o.supports_reference;$('#batch-denoise').disabled=!o.supports_reference;
 if(!o.supports_reference){batchReference='';$('#batch-reference-preview').hidden=true;$('#batch-clear-reference').hidden=true;$('#batch-file-reference').value='';}
 $('#batch-capability-hint').textContent=qwen?'Qwen utiliza su modelo, VAE y sampler fijos. Para usar LoRAs o una imagen inicial, elige ComfyUI o Automatic1111 / Forge.':'Se aplican únicamente LoRAs y VAE compatibles con la arquitectura elegida. Los adaptadores de vídeo u otras arquitecturas aparecen deshabilitados.';
 renderBatchLoras();
}
function renderBatchLoras(){
 const separate=batchValue('engine')==='comfy';
 $('#batch-selected-loras').innerHTML=batchLoraSelection.map((l,i)=>`<div class="batch-lora-row"><strong>${esc(l.name)}</strong><label>Intensidad ${separate?'modelo':''}<input type="number" data-batch-lora-index="${i}" data-batch-lora-field="strength_model" min="-2" max="2" step="0.05" value="${l.strength_model}"></label>${separate?`<label>Intensidad CLIP<input type="number" data-batch-lora-index="${i}" data-batch-lora-field="strength_clip" min="-2" max="2" step="0.05" value="${l.strength_clip}"></label>`:''}<button type="button" class="secondary-button" data-remove-batch-lora="${i}">Quitar</button></div>`).join('')||'<p class="video-hint">Sin LoRAs seleccionadas.</p>';
}
async function loadBatchControlOptions(engine=batchValue('engine'),saved=null,refresh=false){
 $('#batch-engine').value=engine;
 const id=++batchControlRequest;$('#batch-options-status').textContent='Leyendo los componentes del motor…';batchControlOptions=null;
 $('#batch-model').disabled=true;
 try{
  const o=await api('image-options?engine='+encodeURIComponent(engine)+(refresh?'&refresh=1':''));if(id!==batchControlRequest)return;
  batchControlOptions=o;$('#batch-engine').value=engine;
  $('#batch-model').innerHTML=o.models.map(m=>batchOption(m.name,`${m.name} · ${m.architecture}`)).join('');$('#batch-model').disabled=false;
  $('#batch-sampler').innerHTML=batchOption('','Predeterminado del motor')+o.samplers.map(s=>batchOption(s,s)).join('');
  $('#batch-scheduler').innerHTML=batchOption('','Predeterminado del motor')+o.schedulers.map(s=>batchOption(s,s)).join('');
  $('#batch-sampler').disabled=engine==='qwen';$('#batch-scheduler').disabled=engine==='qwen';
  if(saved){
   batchReference=saved.input_image||'';$('#batch-reference-preview').hidden=!batchReference;$('#batch-clear-reference').hidden=!batchReference;
   for(const key of ['model','width','height','steps','cfg','seed','negative','sampler','scheduler'])if(saved[key]!=null)$('#batch-'+key).value=saved[key];
   batchLoraSelection=(saved.loras||[]).map(l=>({...l}));
  }else{batchLoraSelection=[];$('#batch-steps').value=engine==='qwen'?8:20;$('#batch-cfg').value=engine==='qwen'?1:7;}
  refreshBatchAssetChoices();
  if(saved?.vae&&[...$('#batch-vae').options].some(v=>v.value===saved.vae&&!v.disabled))$('#batch-vae').value=saved.vae;
  if(saved?.input_image&&o.supports_reference){batchReference=saved.input_image;$('#batch-reference-preview').src='/inputs/'+encodeURIComponent(batchReference);$('#batch-reference-preview').hidden=false;$('#batch-clear-reference').hidden=false;}
  if(saved?.denoise!=null)$('#batch-denoise').value=saved.denoise;
  $('#batch-options-status').textContent=`${o.models.length} modelos · ${o.loras.length} LoRAs detectadas. Estos ajustes pertenecen al lote.`;
 }catch(e){if(id===batchControlRequest){$('#batch-model').innerHTML=batchOption('','Conecta el motor y actualiza');$('#batch-options-status').textContent=e.message;}}
}
function loadBatchControls(){if(!batchControlOptions)loadBatchControlOptions();}
function readBatchControls(){
 if(!batchControlOptions)throw Error('Conecta el motor y pulsa Actualizar componentes antes de guardar el lote.');
 for(const el of $('#batch-controls').querySelectorAll('input[type="number"]'))if(!el.disabled&&!el.reportValidity())throw Error('Revisa los ajustes numéricos del lote.');
 return {engine:batchValue('engine'),model:batchValue('model'),width:Number(batchValue('width')),height:Number(batchValue('height')),steps:Number(batchValue('steps')),cfg:Number(batchValue('cfg')),seed:Number(batchValue('seed')),negative:batchValue('negative'),vae:batchValue('vae'),sampler:batchValue('sampler'),scheduler:batchValue('scheduler'),loras:batchLoraSelection.map(l=>({...l})),input_image:batchReference,denoise:Number(batchValue('denoise'))};
}
$('#batch-engine').onchange=()=>loadBatchControlOptions();
$('#batch-model').onchange=refreshBatchAssetChoices;
$('#batch-refresh-components').onclick=async()=>{try{const saved=batchControlOptions?readBatchControls():null;await loadBatchControlOptions(batchValue('engine'),saved,true);}catch(e){toast(e.message);}};
$('#batch-add-lora').onclick=()=>{
 const name=batchValue('lora-choice');if(!name)return;
 if(batchLoraSelection.length>=8){toast('Puedes aplicar hasta ocho LoRAs.');return;}
 if(batchLoraSelection.some(l=>l.name===name))return;
 batchLoraSelection.push({name,strength_model:1,strength_clip:1});renderBatchLoras();
};
$('#batch-selected-loras').addEventListener('change',event=>{
 const input=event.target.closest('[data-batch-lora-field]');if(!input)return;
 const row=batchLoraSelection[Number(input.dataset.batchLoraIndex)];if(!row)return;
 row[input.dataset.batchLoraField]=Number(input.value);
 if(batchValue('engine')==='automatic')row.strength_clip=row.strength_model;
});
$('#batch-selected-loras').addEventListener('click',event=>{
 const button=event.target.closest('[data-remove-batch-lora]');if(!button)return;
 batchLoraSelection.splice(Number(button.dataset.removeBatchLora),1);renderBatchLoras();
});
$('#batch-file-reference').onchange=async()=>{
 const file=$('#batch-file-reference').files[0];if(!file)return;
 $('#batch-import').disabled=true;
 try{
  const form=new FormData();form.append('image',file);
  const response=await fetch('/api/image/input',{method:'POST',body:form});
  if(!response.headers.get('Content-Type')?.includes('application/json'))throw Error('Reinicia el servidor actualizado para habilitar la imagen inicial del lote.');
  const result=await response.json();if(!response.ok)throw Error(result.error||'No se pudo cargar la imagen.');
  batchReference=result.name;$('#batch-reference-preview').src=result.url;$('#batch-reference-preview').hidden=false;$('#batch-clear-reference').hidden=false;
 }catch(e){toast(e.message);}finally{$('#batch-import').disabled=!selectedImageBatch;}
};
$('#batch-clear-reference').onclick=()=>{batchReference='';$('#batch-file-reference').value='';$('#batch-reference-preview').hidden=true;$('#batch-clear-reference').hidden=true;};
document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-edit-batch-settings]');if(!button)return;
 const b=state.galleryBatches?.find(v=>v.id===button.dataset.editBatchSettings);if(!b)return;
 editingBatchId=b.id;$('#batch-seed').disabled=true;$('#batch-negative').disabled=true;$('#batch-import').hidden=true;$('#batch-file').disabled=true;$('#batch-editing-label').textContent=`Editando pendientes de «${b.name}». Pausa la cola antes de aplicar; se conservan semillas y negativos de cada imagen.`;
 $('#batch-apply-pending').hidden=false;$('#batch-cancel-edit').hidden=false;
 await loadBatchControlOptions(b.settings?.engine||'comfy',b.settings||null);
 $('#batch-controls').scrollIntoView({behavior:'smooth',block:'start'});
});
$('#batch-apply-pending').onclick=async()=>{
 if(!editingBatchId)return;const button=$('#batch-apply-pending');button.disabled=true;
 try{const r=await api('image-batches/'+editingBatchId+'/settings',readBatchControls());toast(`Ajustes guardados en ${r.updated} pendientes. Pulsa Retomar pendientes cuando quieras continuar.`);await loadImageBatches();}catch(e){toast(e.message);}finally{button.disabled=false;}
};
$('#batch-cancel-edit').onclick=()=>{editingBatchId=null;$('#batch-seed').disabled=false;$('#batch-negative').disabled=false;$('#batch-import').hidden=false;$('#batch-file').disabled=false;$('#batch-editing-label').textContent='';$('#batch-apply-pending').hidden=true;$('#batch-cancel-edit').hidden=true;};

if(new URLSearchParams(location.search).get('view')==='batches')setView('batches');

"use strict";
const tune={active:false,region:null,level:null,text:null,selected:null,wholePart:false};
const positionNames={'bottom-left':'左下','top-left':'左上','top-right':'右上','bottom-right':'右下','top-center':'中上','bottom-center':'中下','middle-left':'左中','middle-right':'右中','middle-center':'中心'};
const positionOptions=(value,inherit=false)=>(inherit?'<option value="">跟随区域 / 全局</option>':'')+AtlasUI.positions.map(p=>`<option value="${p}" ${p===value?'selected':''}>${positionNames[p]}</option>`).join('');
const historyCache=AtlasUI.editHistory(60);
let textLayers,placementFrame,dragLabel=null,inlineEditor=null,addMenu=null,lastTextStyle=null;
const snapshotEdits=()=>({levels:annotations,regions:regionNames,style:AtlasUI.readerStyle(prefs)});
function remember(key){historyCache.record(snapshotEdits(),key);syncHistoryButtons()}
function syncHistoryButtons(){for(const [id,enabled]of [['tune-undo',historyCache.canUndo],['tune-redo',historyCache.canRedo]])if($(id))$(id).disabled=!enabled}
function restoreHistory(direction){
  finishInline(false);closeAddMenu();const next=historyCache[direction](snapshotEdits());if(!next)return;
  annotations=next.levels;regionNames=next.regions;Object.assign(prefs,next.style);saveEditorial();applyPrefs();options();map.closePopup();render();
}
function regionRecord(id=tune.region){return regionNames[regionKey(id)]||{}}
function regionStyle(id){return {...AtlasUI.mapStyle(prefs),...regionRecord(id).style}}
function entryRegion(l,xy=l.entries[0].coordinates){return l.region_ids.find(id=>{const r=regions.get(id);return r&&inRegion(r,xy[0],xy[1])})||l.region_ids[0]}
function patchRegion(id,patch){regionNames[regionKey(id)]={...regionRecord(id),...patch};saveEditorial()}
function redrawMap(){drawRegions();drawMarkers();drawAnnotations();requestLabelPlacement()}
function readerControls(prefix,regional=false){
  const scope=regional?'data-regional="1"':'',range=(key,title,min,max,step)=>`<label>${title}<output data-value="${key}" ${scope}></output><input data-pref="${key}" ${scope} aria-label="${prefix}${title}" type="range" min="${min}" max="${max}" step="${step}"></label>`;
  return range('point','标点大小',.6,2.6,.1)+range('regionLabel','区域标签字号',10,42,1)+range('levelLabel','关卡标签字号',10,42,1)+
    `<label>区域标签默认位置<select data-pref="regionPosition" ${scope} aria-label="${prefix}区域标签默认位置">${positionOptions('')}</select></label>
    <label>关卡标签默认位置<select data-pref="levelPosition" ${scope} aria-label="${prefix}关卡标签默认位置">${positionOptions('')}</select></label>
    <div class="field-pair"><label>水平偏移 px<input data-pref="offsetX" ${scope} aria-label="${prefix}关卡标签水平偏移" type="number" min="0" max="80" step="1"></label><label>垂直偏移 px<input data-pref="offsetY" ${scope} aria-label="${prefix}关卡标签垂直偏移" type="number" min="0" max="80" step="1"></label></div>`+
    (regional?'':`<div class="label-switches"><label><input data-pref="adaptPositions" type="checkbox">位置适应</label><label><input data-pref="levelLabels" type="checkbox">关卡标签</label><label class="custom-text-toggle"><input data-pref="customTexts" type="checkbox">自定义文本</label></div><div class="settings-actions"><button data-reset-global>恢复默认</button><button data-reset-all>重置所有更改</button></div>`);
}
function syncStyleControls(){
  for(const el of document.querySelectorAll('[data-pref]')){
    const source=el.dataset.regional?regionStyle(tune.region):prefs,key=el.dataset.pref;
    if(el.type==='checkbox')el.checked=source[key];else el.value=source[key];
  }
  for(const el of document.querySelectorAll('[data-value]')){const key=el.dataset.value,v=(el.dataset.regional?regionStyle(tune.region):prefs)[key];el.textContent=key==='point'?`${v.toFixed(1)}×`:`${v}px`}
  const hasTexts=Object.values(regionNames).some(r=>r.texts?.length);
  for(const el of document.querySelectorAll('.custom-text-toggle'))el.hidden=!hasTexts;
}
function regionPlacement(r){return regionRecord(r.id).labelPosition||regionStyle(r.id).regionPosition}
function requestLabelPlacement(){
  cancelAnimationFrame(placementFrame);
  if(!AtlasUI.adaptiveEnabled(prefs,state)||inlineEditor||dragLabel)return;
  placementFrame=requestAnimationFrame(()=>{
    if(!AtlasUI.adaptiveEnabled(prefs,state)||inlineEditor||dragLabel)return;
    const shell=$('map').getBoundingClientRect();
    const obstacles=[...$('map').querySelectorAll('.dot-pin,.pin-number,.pin-prefix,.free-text,.leaflet-control-zoom'),...document.querySelectorAll('.route-controls,.map-key')].map(el=>el.getBoundingClientRect()).filter(r=>r.right>shell.left&&r.left<shell.right&&r.bottom>shell.top&&r.top<shell.bottom);
    const placements=[];
    for(const el of $('map').querySelectorAll('.region-label')){
      const content=el.querySelector('.region-label-content'),bounds=el.getBoundingClientRect();
      if(!content||bounds.right<shell.left||bounds.left>shell.right||bounds.bottom<shell.top||bounds.top>shell.bottom)continue;
      const rect=content.getBoundingClientRect(),r=regions.get(content.dataset.regionEditor);
      placements.push([content,AtlasUI.chooseRegionPosition(bounds,{width:rect.width,height:rect.height},obstacles,regionPlacement(r))]);
    }
    for(const [content,position]of placements)if(content.dataset.position!==position)content.dataset.position=position;
  });
}
function labelPositionStyle(l,d,xy){
  const a={...l.manual,...annotations[l.level_id]},base=regionStyle(entryRegion(l,xy)),s=AtlasUI.levelLabelStyle(a.labelPosition||base.levelPosition,base.offsetX,base.offsetY,a.labelShiftX||0,a.labelShiftY||0);
  return `font-size:${base.levelLabel}px;left:${d/2+s.x}px;top:${d/2+s.y}px;bottom:auto;transform:translate(${s.tx}%,${s.ty}%);`;
}
function canTune(){return Boolean(state.region||state.part)}
function activeTuneRegion(){return regions.get(tune.region)}
function enterTune(id=state.region||availableRegions()[0]?.id){
  if(!regions.has(id)||!availableRegions().some(r=>r.id===id))return;
  finishInline(true);closeAddMenu();settings(false);map.closePopup();
  const whole=!state.region&&Boolean(state.part);if(!whole&&state.region!==id)selectRegion(id);
  Object.assign(tune,{active:true,region:id,wholePart:whole,selected:null,level:null,text:null});
  prefs.sidebarHidden=false;sidebarLayout();document.body.classList.add('tuning');map.doubleClickZoom.disable();render();
}
function leaveTune(redraw=true){
  finishInline(true);closeAddMenu();tune.active=false;tune.selected=null;tune.level=null;tune.text=null;
  document.body.classList.remove('tuning');map.doubleClickZoom.enable();if(redraw)render();
}
function selectElement(type,id,region=tune.region,scroll=true){
  if(!tune.active)return;
  finishInline(true);closeAddMenu();
  tune.selected={type,id,region};tune.level=type==='level'?id:null;tune.text=type==='text'?id:null;
  if(tune.active)tune.region=region;
  renderInspector();for(const el of $('map').querySelectorAll('.free-text'))el.classList.toggle('selected',type==='text'&&el.dataset.textId===id&&el.dataset.textRegion===region);if(tune.active)drawRegions();
  if(prefs.sidebarHidden){prefs.sidebarHidden=false;sidebarLayout()}
  if(scroll)$('sidebar-scroll').scrollTop=0;
}
function inspectLevel(id){const l=byId.get(id);if(!tune.active||!l)return;selectElement('level',id,l.region_ids.includes(tune.region)?tune.region:entryRegion(l))}
function selectedText(){const s=tune.selected;return s?.type==='text'?(regionRecord(s.region).texts||[]).find(t=>t.id===s.id):null}
function renderInspector(){
  const panel=$('element-inspector'),s=tune.selected;
  if(!tune.active||!s){panel.hidden=true;return}
  const r=regions.get(s.region),l=s.type==='level'?byId.get(s.id):null,t=selectedText();
  if((s.type==='text'&&!t)||(s.type==='level'&&!l)||!r){tune.selected=null;panel.hidden=true;return}
  const header=label=>`<div class="inspector-title"><strong>当前编辑元素 · ${label}</strong><button id="inspect-close" aria-label="取消元素选择">×</button></div>`;
  let body='';
  if(l){const a={...l.manual,...annotations[l.level_id]};body=header('关卡标签')+`<div class="element-id">${esc(l.level_id)}</div><p class="hint">${esc(regionTitle(r))} · Del隐藏文字，入口保留。</p>
      <label class="inspector-check"><input id="inspect-visible" type="checkbox" ${a.labelHidden?'':'checked'}>显示此关卡标签</label>
      <label>标签位置<select id="inspect-level-position" aria-label="选中关卡标签位置">${positionOptions(a.labelPosition,true)}</select></label>
      <div class="field-pair"><label>横向微调 px<input id="inspect-shift-x" aria-label="选中关卡横向微调" type="number" min="-200" max="200" value="${a.labelShiftX||0}"></label><label>纵向微调 px<input id="inspect-shift-y" aria-label="选中关卡纵向微调" type="number" min="-200" max="200" value="${a.labelShiftY||0}"></label></div><button id="inspect-level-reset">恢复此标签默认</button>`;
  }else if(t){const style=AtlasUI.textStyle(t);body=header('自定义文本')+`<p class="hint">${esc(regionTitle(r))} · Del删除 · 可拖动或直接编辑</p><label>文字<textarea id="inspect-text" aria-label="选中文字内容" rows="2" maxlength="300">${esc(t.text)}</textarea></label>
      <div class="field-pair"><label>字号 px<input id="inspect-text-size" aria-label="选中文字字号" type="number" min="10" max="72" value="${style.size}"></label><label>颜色<input id="inspect-text-color" aria-label="选中文字颜色" type="color" value="${style.color}"></label></div>
      <div class="field-pair"><label>描边 px<input id="inspect-text-stroke" aria-label="选中文字描边大小" type="number" min="0" max="8" step=".5" value="${style.strokeWidth}"></label><label>描边颜色<input id="inspect-text-stroke-color" aria-label="选中文字描边颜色" type="color" value="${style.strokeColor}"></label></div><div class="dialog-actions"><button id="inspect-inline">在地图中编辑</button><button id="inspect-delete">删除文字</button></div>`;
  }else body=header('区域名称')+`<label>区域名称<input id="inspect-region-name" aria-label="选中区域名称" maxlength="80" value="${esc(regionTitle(r))}"></label><p class="hint">也可点击地图上的区域名称直接编辑。</p>`;
  panel.hidden=false;panel.innerHTML=body;
  $('inspect-close').onclick=()=>{finishInline(true);tune.selected=null;tune.level=null;tune.text=null;renderInspector()};
  if(l){
    $('inspect-visible').onchange=e=>{remember(`visibility:${l.level_id}`);annotations[l.level_id]={...annotations[l.level_id],labelHidden:!e.target.checked};saveEditorial();drawMarkers();requestLabelPlacement()};
    const save=()=>{remember(`label:${l.level_id}`);annotations[l.level_id]={...annotations[l.level_id],labelPosition:$('inspect-level-position').value,labelShiftX:clamp($('inspect-shift-x').value,-200,200,0),labelShiftY:clamp($('inspect-shift-y').value,-200,200,0)};saveEditorial();drawMarkers();requestLabelPlacement()};
    $('inspect-level-position').onchange=save;for(const id of ['inspect-shift-x','inspect-shift-y'])$(id).oninput=save;
    $('inspect-level-reset').onclick=()=>{remember();const a={...annotations[l.level_id]};for(const k of ['labelPosition','labelShiftX','labelShiftY','labelHidden'])delete a[k];annotations[l.level_id]=a;saveEditorial();drawMarkers();renderInspector();requestLabelPlacement()};
  }else if(t){
    for(const id of ['inspect-text','inspect-text-size','inspect-text-color','inspect-text-stroke','inspect-text-stroke-color'])$(id).oninput=e=>{
      const style=AtlasUI.textStyle({size:Number($('inspect-text-size').value),color:$('inspect-text-color').value,strokeWidth:Number($('inspect-text-stroke').value),strokeColor:$('inspect-text-stroke-color').value});
      remember(`text:${t.id}:${e.target.id}`);patchRegion(s.region,{texts:(regionRecord(s.region).texts||[]).map(v=>v.id===t.id?{...v,text:$('inspect-text').value.slice(0,300),...style}:v)});
      if(e.target.id!=='inspect-text')lastTextStyle=style;drawAnnotations();requestLabelPlacement();
    };
    $('inspect-delete').onclick=deleteSelected;
    $('inspect-inline').onclick=()=>{if(!tune.active)enterTune(s.region);selectElement('text',t.id,s.region);drawAnnotations();startInline('text',t.id,s.region)};
  }else $('inspect-region-name').onchange=e=>renameRegion(r.id,e.target.value);
}
function renderTunePanel(){
  $('tune-panel').hidden=!tune.active;
  if(!tune.active){renderInspector();return}
  const r=activeTuneRegion();if(!r){leaveTune();return}
  const custom=Boolean(regionRecord().style);
  $('tune-panel').innerHTML=`<div class="tune-heading"><strong>区域微调</strong><div class="edit-actions"><button id="tune-undo" title="Ctrl+Z" aria-label="撤销编辑">↶</button><button id="tune-redo" title="Ctrl+Shift+Z" aria-label="重做编辑">↷</button><button id="tune-done">完成</button></div></div>
    <p class="hint">点击名称原位改名；点击编号或文字后在上方编辑。双击区域空白处添加文本。Del 删除/隐藏，Ctrl+Z 撤销。</p>
    <label>编辑区域<select id="tune-region" aria-label="微调区域">${availableRegions().map(q=>`<option value="${esc(q.id)}" ${r.id===q.id?'selected':''}>${esc(regionTitle(q))}</option>`).join('')}</select></label>
    <div class="field-pair"><label>本区域标签位置<select id="tune-region-position" aria-label="本区域标签位置">${positionOptions(regionRecord().labelPosition,true)}</select></label><button id="tune-batch">批量名称…</button></div>
    <label class="scope-switch"><input id="tune-global" type="checkbox" ${custom?'':'checked'}>使用全局样式</label><div class="reader-controls">${readerControls('微调·',true)}</div>`;
  syncStyleControls();syncHistoryButtons();renderInspector();
  $('tune-done').onclick=()=>leaveTune();$('tune-undo').onclick=()=>restoreHistory('undo');$('tune-redo').onclick=()=>restoreHistory('redo');
  $('tune-region').onchange=e=>{const id=e.target.value;leaveTune(false);selectRegion(id);enterTune(id)};
  $('tune-batch').onclick=()=>{openRegionNames();$('region-batch-open').click()};
  $('tune-global').onchange=e=>{remember();const record={...regionRecord()};if(e.target.checked)delete record.style;else record.style=AtlasUI.mapStyle(prefs);regionNames[regionKey(tune.region)]=record;saveEditorial();redrawMap();renderTunePanel()};
  $('tune-region-position').onchange=e=>{remember(`region-position:${r.id}`);patchRegion(r.id,{labelPosition:e.target.value});drawRegions();requestLabelPlacement()};
}
function renameRegion(id,value){
  const r=regions.get(id),title=value.trim().slice(0,80);if(!r||!title||title===regionTitle(r))return;
  remember(`name:${id}`);patchRegion(id,{title});options();redrawMap();sidebar();
}
function startInline(type,id,region=tune.region){
  if(!tune.active)return;
  finishInline(true);selectElement(type,id,region,false);
  const node=type==='region'?$('map').querySelector(`[data-region-editor="${CSS.escape(id)}"] .region-title`):$('map').querySelector(`[data-text-id="${CSS.escape(id)}"][data-text-region="${CSS.escape(region)}"]`);
  if(!node)return;
  const original=type==='region'?regionTitle(regions.get(id)):selectedText()?.text||'';
  inlineEditor={node,type,id,region,original};node.contentEditable='plaintext-only';node.setAttribute('role','textbox');node.setAttribute('aria-label',type==='region'?'地图内编辑区域名称':'地图内编辑文本');node.classList.add('inline-editor');map.dragging.disable();node.focus();
  const range=document.createRange();range.selectNodeContents(node);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);
  node.onblur=()=>finishInline(true);
  node.onkeydown=e=>{if(e.key==='Escape'||e.key==='Enter'&&!e.shiftKey){e.preventDefault();e.stopPropagation();finishInline(e.key!=='Escape')}};
}
function finishInline(save){
  if(!inlineEditor)return;const edit=inlineEditor;inlineEditor=null;
  const value=(edit.node.innerText||'').trim().slice(0,edit.type==='region'?80:300);
  edit.node.onblur=null;edit.node.onkeydown=null;edit.node.removeAttribute('contenteditable');edit.node.removeAttribute('role');edit.node.removeAttribute('aria-label');edit.node.classList.remove('inline-editor');map.dragging.enable();
  if(save&&value&&value!==edit.original){
    if(edit.type==='region'){renameRegion(edit.id,value);return}
    remember(`text:${edit.id}`);patchRegion(edit.region,{texts:(regionRecord(edit.region).texts||[]).map(t=>t.id===edit.id?{...t,text:value}:t)});
  }
  edit.node.textContent=save&&value?value:edit.original;drawAnnotations();renderInspector();requestLabelPlacement();
}
function deleteSelected(){
  const s=tune.selected;if(!s||!tune.active)return;finishInline(false);
  if(s.type==='text'){remember();patchRegion(s.region,{texts:(regionRecord(s.region).texts||[]).filter(t=>t.id!==s.id)});tune.selected=null;tune.text=null;}
  else if(s.type==='level'){remember();annotations[s.id]={...annotations[s.id],labelHidden:true};saveEditorial();}
  else return;
  redrawMap();renderInspector();syncStyleControls();
}
function inRegion(r,x,y){const[a,b,c,d]=r.bounds;return x>=a&&x<=c&&y>=b&&y<=d}
function drawAnnotations(){
  if(!textLayers||inlineEditor)return;textLayers.clearLayers();if(!prefs.customTexts)return;
  for(const r of availableRegions()){
    if(state.region&&state.region!==r.id)continue;
    for(const t of regionRecord(r.id).texts||[]){
      if(!inRegion(r,t.x,t.y))continue;
      const s=AtlasUI.textStyle(t),editing=tune.active&&(tune.wholePart||tune.region===r.id);
      const marker=L.marker([t.y,t.x],{pane:'editorText',draggable:editing,interactive:editing,keyboard:editing,icon:L.divIcon({className:`text-marker ${editing?'editable':''}`,iconSize:[0,0],iconAnchor:[0,0],html:`<span data-text-id="${esc(t.id)}" data-text-region="${esc(r.id)}" class="free-text ${tune.selected?.type==='text'&&tune.selected.id===t.id&&tune.selected.region===r.id?'selected':''}" style="font-size:${s.size}px;color:${s.color};-webkit-text-stroke:${s.strokeWidth}px ${s.strokeColor}">${esc(t.text)}</span>`})}).addTo(textLayers);
      marker.on('click',e=>{L.DomEvent.stop(e.originalEvent);selectElement('text',t.id,r.id)});
      marker.on('dragstart',()=>{finishInline(true);selectElement('text',t.id,r.id,false);remember()});
      marker.on('dragend',()=>{const pos=marker.getLatLng(),[a,b,c,d]=r.bounds;patchRegion(r.id,{texts:(regionRecord(r.id).texts||[]).map(v=>v.id===t.id?{...v,x:clamp(pos.lng,a,c,a),y:clamp(pos.lat,b,d,b)}:v)});drawAnnotations();renderInspector();requestLabelPlacement()});
    }
  }
}
function closeAddMenu(){if(addMenu){addMenu.remove();addMenu=null}}
function showAddMenu(r,x,y,clientX,clientY){
  closeAddMenu();const host=document.querySelector('.map-shell'),rect=host.getBoundingClientRect();
  addMenu=document.createElement('div');addMenu.className='add-text-menu';addMenu.style.left=`${clamp(clientX-rect.left,4,Math.max(4,rect.width-150),4)}px`;addMenu.style.top=`${clamp(clientY-rect.top,4,Math.max(4,rect.height-42),4)}px`;
  addMenu.innerHTML='<button type="button"><svg class="text-tool-icon" viewBox="0 0 1024 1024" aria-hidden="true" focusable="false"><path d="M307.2 409.6h153.6v307.2h102.4V409.6h153.6v-102.4H307.2zM76.8 460.8h102.4v102.4H76.8zM844.8 460.8h102.4v102.4h-102.4z" fill="currentColor"/><path d="M102.4 102.4v307.2h51.2V153.6h716.8v256h51.2V102.4zM870.4 870.4H153.6V614.4H102.4v307.2h819.2V614.4h-51.2z" fill="currentColor" opacity=".7"/></svg> 添加文本</button>';host.append(addMenu);
  addMenu.querySelector('button').onclick=()=>{
    const style=lastTextStyle||AtlasUI.textStyle({size:regionStyle(r.id).regionLabel}),t={id:crypto.randomUUID(),text:'文本',x,y,...style};
    remember(`text:${t.id}`);patchRegion(r.id,{texts:[...(regionRecord(r.id).texts||[]),t]});prefs.customTexts=true;applyPrefs();selectElement('text',t.id,r.id);drawAnnotations();syncStyleControls();startInline('text',t.id,r.id);
  };
}
function resetGlobal(){remember();Object.assign(prefs,AtlasUI.defaults);applyPrefs();redrawMap();renderTunePanel()}
function resetAllStyles(){ $('style-reset-dialog').showModal() }
function applyResetAllStyles(){
  finishInline(true);remember();const reset=AtlasUI.resetMapStyles(annotations,regionNames);annotations=reset.levels;regionNames=reset.regions;Object.assign(prefs,AtlasUI.defaults,{regionLabels:false,levelLabels:true,customTexts:true,adaptPositions:true});lastTextStyle=null;saveEditorial();applyPrefs();redrawMap();renderTunePanel();
}
function regionAt(point){return data.regions.find(r=>inRegion(r,point.lng,point.lat))}
function initEditor(){
  map.createPane('editorText');map.getPane('editorText').style.zIndex=640;map.getPane('editorText').style.pointerEvents='none';textLayers=L.layerGroup().addTo(map);
  $('reader-controls').innerHTML=readerControls('设置·');syncStyleControls();
  $('style-reset-cancel').onclick=()=>$('style-reset-dialog').close();$('style-reset-confirm').onclick=()=>{$('style-reset-dialog').close();applyResetAllStyles()};
  $('sources-toggle').onclick=()=>{const open=$('sources-content').hidden;$('sources-content').hidden=!open;$('sources-toggle').setAttribute('aria-expanded',open);$('sources-toggle').textContent=(open?'▾':'▸')+' 数据与来源'};
  document.addEventListener('click',e=>{if(e.target.closest('[data-reset-global]'))resetGlobal();if(e.target.closest('[data-reset-all]'))resetAllStyles()});
  document.addEventListener('input',e=>{
    const key=e.target.dataset.pref;if(!key)return;
    const value=e.target.type==='checkbox'?e.target.checked:['range','number'].includes(e.target.type)?Number(e.target.value):e.target.value;
    remember(`style:${e.target.dataset.regional?tune.region:'global'}:${key}`);
    const update=AtlasUI.readerStyle({[key]:value});
    if(e.target.dataset.regional&&regionRecord().style)patchRegion(tune.region,{style:{...regionRecord().style,...AtlasUI.mapStyle(update)}});else Object.assign(prefs,update);
    applyPrefs();redrawMap();
  });
  document.addEventListener('pointerdown',e=>{if(!e.target.closest('.add-text-menu'))closeAddMenu()});
  const container=$('map');
  container.addEventListener('click',e=>{
    const label=e.target.closest('[data-region-editor]');
    if(!label)return;
    e.stopPropagation();
    if(e.target.isContentEditable)return;
    if(tune.active&&label.dataset.regionEditor===tune.region){if(e.detail===1)startInline('region',tune.region);return}
    if(tune.active)leaveTune();
  },true);
  container.addEventListener('dblclick',e=>{
    const label=e.target.closest('[data-region-editor]'),text=e.target.closest('[data-text-id]');
    if(e.target.isContentEditable)return;
    if(label){e.preventDefault();e.stopPropagation();finishInline(true);leaveTune(false);selectRegion(label.dataset.regionEditor);enterTune(label.dataset.regionEditor);return}
    if(text&&tune.active){e.preventDefault();e.stopPropagation();startInline('text',text.dataset.textId,text.dataset.textRegion);return}
    if(e.target.closest('.number-pin,.free-text,.leaflet-control,.leaflet-popup,.add-text-menu'))return;
    const point=map.mouseEventToLatLng(e),r=regionAt(point);if(!r)return;
    e.preventDefault();e.stopPropagation();finishInline(true);
    if(!tune.active){selectRegion(r.id);return}
    if(r.id!==tune.region){leaveTune(false);selectRegion(r.id);enterTune(r.id);return}
    showAddMenu(r,point.lng,point.lat,e.clientX,e.clientY);
  },true);
  document.addEventListener('keydown',e=>{
    if($('style-reset-dialog').open||$('region-dialog').open)return;
    const textInput=e.target.isContentEditable||e.target.tagName==='TEXTAREA'||e.target.tagName==='INPUT'&&['text','search','url','email','password'].includes(e.target.type);
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'&&!textInput){e.preventDefault();e.stopImmediatePropagation();restoreHistory(e.shiftKey?'redo':'undo');return}
    if(e.key==='Delete'&&tune.active&&!textInput&&!['INPUT','SELECT'].includes(e.target.tagName)) {e.preventDefault();deleteSelected();return}
    if(e.key==='Escape'&&tune.active&&!inlineEditor&&!$('region-dialog').open&&$('settings').hidden){e.preventDefault();leaveTune()}
  },true);
  map.on('moveend',requestLabelPlacement);
  map.on('click',e=>{
    if(e.originalEvent?.target.closest('.inline-editor,.number-pin,.free-text'))return;
    const r=regionAt(e.latlng);if(!r)return;
    if(tune.active&&r.id===tune.region){finishInline(true);tune.selected=null;tune.level=null;tune.text=null;renderInspector();return}
    if(tune.active)leaveTune();
  });
  container.addEventListener('pointerdown',e=>{
    const label=e.target.closest('[data-drag-level]');if(!tune.active||!label||e.button!==0||e.target.isContentEditable)return;
    const id=label.dataset.dragLevel,l=byId.get(id);if(!l)return;
    const region=l.region_ids.includes(tune.region)?tune.region:entryRegion(l);selectElement('level',id,region);
    e.preventDefault();e.stopPropagation();map.dragging.disable();label.setPointerCapture(e.pointerId);
    const a={...l.manual,...annotations[id]};dragLabel={label,id,pointer:e.pointerId,x:e.clientX,y:e.clientY,left:parseFloat(label.style.left),top:parseFloat(label.style.top),sx:a.labelShiftX||0,sy:a.labelShiftY||0};
  },true);
  container.addEventListener('pointermove',e=>{if(!dragLabel)return;const d=dragLabel;d.dx=clamp(e.clientX-d.x,-200-d.sx,200-d.sx,0);d.dy=clamp(e.clientY-d.y,-200-d.sy,200-d.sy,0);d.label.style.left=`${d.left+d.dx}px`;d.label.style.top=`${d.top+d.dy}px`});
  const end=()=>{
    if(!dragLabel)return;const d=dragLabel;dragLabel=null;
    if(d.label.hasPointerCapture(d.pointer))d.label.releasePointerCapture(d.pointer);map.dragging.enable();
    if(Math.abs(d.dx||0)+Math.abs(d.dy||0)>1){remember();annotations[d.id]={...annotations[d.id],labelShiftX:d.sx+(d.dx||0),labelShiftY:d.sy+(d.dy||0)};saveEditorial();drawMarkers()}
    renderInspector();requestLabelPlacement();
  };
  container.addEventListener('pointerup',end);container.addEventListener('pointercancel',end);
  container.addEventListener('click',e=>{if(tune.active&&e.target.closest('[data-drag-level]')){e.stopPropagation();e.preventDefault()}},true);
  drawAnnotations();requestLabelPlacement();
}

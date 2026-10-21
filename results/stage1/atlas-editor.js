'use strict';
const tune={active:false,region:null,level:null,text:null,adding:false,wholePart:false};
const positionNames={'bottom-left':'左下','top-left':'左上','top-right':'右上','bottom-right':'右下','top-center':'中上','bottom-center':'中下','middle-left':'左中','middle-right':'右中','middle-center':'中中'};
const positionOptions=(value,inherit=false)=>(inherit?'<option value="">跟随全局</option>':'')+AtlasUI.positions.map(p=>`<option value="${p}" ${p===value?'selected':''}>${positionNames[p]}</option>`).join('');
let textLayers,placementFrame,dragLabel=null;

function readerControls(prefix){
  const range=(key,title,min,max,step)=>`<label>${title}<output data-value="${key}"></output><input data-pref="${key}" aria-label="${prefix}${title}" type="range" min="${min}" max="${max}" step="${step}"></label>`;
  return range('point','标点大小',.6,2.6,.1)+range('regionLabel','区域标签字号',10,42,1)+range('levelLabel','关卡标签字号',10,42,1)+
    `<label>区域标签默认位置<select data-pref="regionPosition" aria-label="${prefix}区域标签默认位置">${positionOptions(prefs.regionPosition)}</select></label>
    <label>关卡标签默认位置<select data-pref="levelPosition" aria-label="${prefix}关卡标签默认位置">${positionOptions(prefs.levelPosition)}</select></label>
    <div class="field-pair"><label>水平偏移 px<input data-pref="offsetX" aria-label="${prefix}关卡标签水平偏移" type="number" min="0" max="80" step="1"></label><label>垂直偏移 px<input data-pref="offsetY" aria-label="${prefix}关卡标签垂直偏移" type="number" min="0" max="80" step="1"></label></div>
    <div class="label-switches"><label><input data-pref="regionLabels" type="checkbox">区域标签</label><label><input data-pref="levelLabels" type="checkbox">关卡标签</label></div>`;
}
function syncStyleControls(){
  document.querySelectorAll('[data-pref]').forEach(el=>{
    const key=el.dataset.pref;if(el.type==='checkbox')el.checked=prefs[key];else el.value=prefs[key];
  });
  document.querySelectorAll('[data-value]').forEach(el=>{const key=el.dataset.value;el.textContent=key==='point'?`${prefs.point.toFixed(1)}×`:`${prefs[key]}px`});
}
function regionRecord(id=tune.region){return regionNames[regionKey(id)]||{}}
function patchRegion(id,patch){regionNames[regionKey(id)]={...regionRecord(id),...patch};saveEditorial()}
function regionPlacement(r){return regionRecord(r.id).labelPosition||prefs.regionPosition}
function requestLabelPlacement(){
  cancelAnimationFrame(placementFrame);placementFrame=requestAnimationFrame(()=>{
    const shell=$('map').getBoundingClientRect();
    const obstacles=[...$('map').querySelectorAll('.dot-pin,.pin-number,.pin-prefix,.free-text,.leaflet-control-zoom'),...document.querySelectorAll('.route-controls,.map-key')].map(el=>el.getBoundingClientRect()).filter(r=>r.right>shell.left&&r.left<shell.right&&r.bottom>shell.top&&r.top<shell.bottom);
    $('map').querySelectorAll('.region-label').forEach(el=>{
      const content=el.querySelector('.region-label-content');if(!content)return;
      const bounds=el.getBoundingClientRect();if(bounds.right<shell.left||bounds.left>shell.right||bounds.bottom<shell.top||bounds.top>shell.bottom)return;
      const rect=content.getBoundingClientRect(),r=regions.get(content.dataset.regionEditor);
      const position=AtlasUI.chooseRegionPosition(bounds,{width:rect.width,height:rect.height},obstacles,regionPlacement(r));
      content.dataset.position=position;
    });
  });
}
function labelPositionStyle(l,d){
  const a={...l.manual,...annotations[l.level_id]},s=AtlasUI.levelLabelStyle(a.labelPosition||prefs.levelPosition,prefs.offsetX,prefs.offsetY,a.labelShiftX||0,a.labelShiftY||0);
  return `left:${d/2+s.x}px;top:${d/2+s.y}px;bottom:auto;transform:translate(${s.tx}%,${s.ty}%);`;
}
function canTune(){return Boolean(state.region||state.part)}
function activeTuneRegion(){return regions.get(tune.region)}
function enterTune(id=state.region||availableRegions()[0]?.id){
  if(!regions.has(id)||!availableRegions().some(r=>r.id===id))return;
  settings(false);map.closePopup();tune.wholePart=!state.region&&Boolean(state.part);tune.active=true;tune.region=id;tune.level=null;tune.text=null;tune.adding=false;
  if(!tune.wholePart&&state.region!==id)selectRegion(id);
  prefs.sidebarHidden=false;sidebarLayout();document.body.classList.add('tuning');map.doubleClickZoom.disable();render();
}
function leaveTune(){
  tune.active=false;tune.adding=false;document.body.classList.remove('tuning','adding-text');map.doubleClickZoom.enable();render();
}
function renderTunePanel(){
  $('tune-panel').hidden=!tune.active;if(!tune.active)return;
  const r=activeTuneRegion();if(!r){leaveTune();return}
  const levels=visible().filter(l=>l.region_ids.includes(r.id));
  if(!levels.some(l=>l.level_id===tune.level))tune.level=levels[0]?.level_id||null;
  const a=annotations[tune.level]||{},texts=regionRecord().texts||[],t=texts.find(t=>t.id===tune.text);
  $('tune-panel').innerHTML=`<div class="tune-heading"><strong>区域微调</strong><button id="tune-done">完成</button></div>
    <label>编辑区域<select id="tune-region" aria-label="微调区域">${availableRegions().map(q=>`<option value="${esc(q.id)}" ${r.id===q.id?'selected':''}>${esc(regionTitle(q))}</option>`).join('')}</select></label>
    <label>区域名称<input id="tune-name" aria-label="微调区域名称" maxlength="80" value="${esc(regionTitle(r))}"></label>
    <div class="field-pair"><label>本区域标签位置<select id="tune-region-position" aria-label="本区域标签位置">${positionOptions(regionRecord().labelPosition,true)}</select></label><button id="tune-batch">批量名称…</button></div>
    <details open><summary>阅读样式 · 全局</summary><div class="reader-controls">${readerControls('微调·')}</div></details>
    <details open><summary>当前关卡标签</summary><p class="hint">可在地图上直接拖动编号；入口标点保持原位。</p>
    <select id="tune-level" aria-label="微调关卡">${levels.map(l=>`<option value="${esc(l.level_id)}" ${l.level_id===tune.level?'selected':''}>${state.part?'':partName(l.shown[0].part)+' · '}${l.shown[0].ordinal} ${esc(l.level_id)}</option>`).join('')}</select>
    <label>编号位置<select id="tune-level-position" aria-label="当前关卡标签位置">${positionOptions(a.labelPosition,true)}</select></label>
    <div class="field-pair"><label>横向微调 px<input id="tune-shift-x" aria-label="当前关卡横向微调" type="number" min="-200" max="200" value="${a.labelShiftX||0}"></label><label>纵向微调 px<input id="tune-shift-y" aria-label="当前关卡纵向微调" type="number" min="-200" max="200" value="${a.labelShiftY||0}"></label></div><button id="tune-level-reset">重置此编号位置</button></details>
    <details open><summary>区域文字标记</summary><p class="hint">输入文字后点“在地图上添加”，再点击${tune.wholePart?'本分P涉及的任一区域':'本区域'}内的位置。已有文字可拖动。</p>
    <select id="tune-text-select" aria-label="选择文字标记"><option value="">新建文字</option>${texts.map(v=>`<option value="${esc(v.id)}" ${v.id===tune.text?'selected':''}>${esc(v.text)}</option>`).join('')}</select>
    <label>文字<textarea id="tune-text" aria-label="标记文字" maxlength="300" rows="2">${esc(t?.text||'')}</textarea></label>
    <div class="field-pair"><label>字号 px<input id="tune-text-size" aria-label="标记字号" type="number" min="10" max="72" value="${t?.size||22}"></label><label>颜色<input id="tune-text-color" aria-label="标记颜色" type="color" value="${t?.color||'#fff6a8'}"></label></div>
    <div class="field-pair"><label>描边 px<input id="tune-text-stroke" aria-label="标记描边大小" type="number" min="0" max="8" step="0.5" value="${t?.strokeWidth??2}"></label><label>描边颜色<input id="tune-text-stroke-color" aria-label="标记描边颜色" type="color" value="${t?.strokeColor||'#17211c'}"></label></div>
    <div class="dialog-actions"><button id="tune-add-text">${tune.adding?'取消添加':'在地图上添加'}</button><button id="tune-delete-text" ${t?'':'disabled'}>删除选中文字</button></div><p id="tune-status" class="hint" role="status">${tune.adding?'请点击当前区域内的地图位置。':'修改即时保存在本机；可在设置中导出。'}</p></details>`;
  syncStyleControls();
  $('tune-done').onclick=leaveTune;
  $('tune-region').onchange=e=>{tune.region=e.target.value;tune.level=null;tune.text=null;tune.adding=false;document.body.classList.remove('adding-text');if(tune.wholePart)render();else selectRegion(tune.region)};
  $('tune-name').onchange=e=>{const title=e.target.value.trim();if(!title){e.target.value=regionTitle(r);return}patchRegion(r.id,{title:title.slice(0,80)});options();drawRegions();if(state.region)$('list-title').textContent=title;requestLabelPlacement()};
  $('tune-batch').onclick=()=>{openRegionNames();$('region-batch-open').click()};
  $('tune-region-position').onchange=e=>{patchRegion(r.id,{labelPosition:e.target.value});drawRegions();requestLabelPlacement()};
  $('tune-level').onchange=e=>{tune.level=e.target.value;renderTunePanel()};
  const saveLabel=()=>{if(!tune.level)return;annotations[tune.level]={...annotations[tune.level],labelPosition:$('tune-level-position').value,labelShiftX:clamp($('tune-shift-x').value,-200,200,0),labelShiftY:clamp($('tune-shift-y').value,-200,200,0)};saveEditorial();drawMarkers();requestLabelPlacement()};
  $('tune-level-position').onchange=saveLabel;for(const id of ['tune-shift-x','tune-shift-y'])$(id).oninput=saveLabel;
  $('tune-level-reset').onclick=()=>{const a={...annotations[tune.level]};for(const k of ['labelPosition','labelShiftX','labelShiftY'])delete a[k];annotations[tune.level]=a;saveEditorial();drawMarkers();renderTunePanel();requestLabelPlacement()};
  $('tune-text-select').onchange=e=>{tune.text=e.target.value||null;tune.adding=false;document.body.classList.remove('adding-text');drawAnnotations();renderTunePanel()};
  for(const id of ['tune-text','tune-text-size','tune-text-color','tune-text-stroke','tune-text-stroke-color'])$(id).oninput=()=>{if(!tune.text)return;const updated=readTextFields();if(!updated.text.trim())return;patchRegion(r.id,{texts:texts.map(v=>v.id===tune.text?{...v,...updated}:v)});drawAnnotations();requestLabelPlacement()};
  $('tune-add-text').onclick=()=>{if(!tune.adding&&!$('tune-text').value.trim()){$('tune-status').textContent='请先输入要添加的文字。';$('tune-text').focus();return}tune.adding=!tune.adding;document.body.classList.toggle('adding-text',tune.adding);$('tune-add-text').textContent=tune.adding?'取消添加':'在地图上添加';$('tune-status').textContent=tune.adding?'请点击当前区域内的地图位置。':'已取消添加。'};
  $('tune-delete-text').onclick=()=>{patchRegion(r.id,{texts:texts.filter(v=>v.id!==tune.text)});tune.text=null;drawAnnotations();renderTunePanel();requestLabelPlacement()};
}
function readTextFields(){return {text:$('tune-text').value.slice(0,300),...AtlasUI.textStyle({size:Number($('tune-text-size').value),color:$('tune-text-color').value,strokeWidth:Number($('tune-text-stroke').value),strokeColor:$('tune-text-stroke-color').value})}}
function inRegion(r,x,y){const[a,b,c,d]=r.bounds;return x>=a&&x<=c&&y>=b&&y<=d}
function drawAnnotations(){
  if(!textLayers)return;textLayers.clearLayers();
  for(const r of availableRegions()){
    if(state.region&&state.region!==r.id)continue;
    for(const t of regionRecord(r.id).texts||[]){
      if(!inRegion(r,t.x,t.y))continue;
      const s=AtlasUI.textStyle(t),editing=tune.active&&(tune.wholePart||tune.region===r.id);
      const marker=L.marker([t.y,t.x],{pane:'editorText',draggable:editing,interactive:editing,keyboard:editing,icon:L.divIcon({className:`text-marker ${editing?'editable':''}`,iconSize:[0,0],iconAnchor:[0,0],html:`<span class="free-text ${tune.text===t.id&&editing?'selected':''}" style="font-size:${s.size}px;color:${s.color};-webkit-text-stroke:${s.strokeWidth}px ${s.strokeColor}">${esc(t.text)}</span>`})}).addTo(textLayers);
      marker.on('click',e=>{L.DomEvent.stop(e.originalEvent);tune.region=r.id;tune.text=t.id;tune.adding=false;document.body.classList.remove('adding-text');renderTunePanel()});
      marker.on('dragend',()=>{const pos=marker.getLatLng(),[a,b,c,d]=r.bounds;patchRegion(r.id,{texts:(regionRecord(r.id).texts||[]).map(v=>v.id===t.id?{...v,x:clamp(pos.lng,a,c,a),y:clamp(pos.lat,b,d,b)}:v)});drawAnnotations();renderTunePanel();requestLabelPlacement()});
    }
  }
}
function initEditor(){
  map.createPane('editorText');map.getPane('editorText').style.zIndex=640;map.getPane('editorText').style.pointerEvents='none';textLayers=L.layerGroup().addTo(map);
  $('reader-controls').innerHTML=readerControls('设置·');syncStyleControls();
  document.addEventListener('input',e=>{const key=e.target.dataset.pref;if(!key)return;const value=e.target.type==='checkbox'?e.target.checked:e.target.type==='range'||e.target.type==='number'?Number(e.target.value):e.target.value;Object.assign(prefs,AtlasUI.readerStyle({[key]:value}));applyPrefs();drawRegions();drawMarkers();drawAnnotations();requestLabelPlacement()});
  $('map').addEventListener('dblclick',e=>{const el=e.target.closest('[data-region-editor]');if(!el)return;e.preventDefault();e.stopPropagation();enterTune(el.dataset.regionEditor)},true);
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&tune.active&&!$('region-dialog').open&&$('settings').hidden){e.preventDefault();leaveTune()}});
  map.on('moveend',requestLabelPlacement);
  map.on('click',e=>{
    if(!tune.active||!tune.adding)return;const {lng:x,lat:y}=e.latlng,r=tune.wholePart?availableRegions().find(r=>inRegion(r,x,y)):activeTuneRegion();
    if(!r||!inRegion(r,x,y)){$('tune-status').textContent=tune.wholePart?'请在本分P涉及的区域框内添加文字。':'请在当前区域框内添加文字。';return}
    const t={id:crypto.randomUUID(),x,y,...readTextFields()};if(!t.text.trim())return;
    patchRegion(r.id,{texts:[...(regionRecord(r.id).texts||[]),t]});tune.region=r.id;tune.text=t.id;tune.adding=false;document.body.classList.remove('adding-text');drawRegions();drawAnnotations();renderTunePanel();requestLabelPlacement();
  });
  const container=$('map');
  container.addEventListener('pointerdown',e=>{
    const label=e.target.closest('[data-drag-level]');if(!tune.active||!label||e.button!==0||tune.adding)return;
    const id=label.dataset.dragLevel,l=byId.get(id);if(!l)return;if(tune.wholePart)tune.region=l.region_ids.find(id=>availableRegions().some(r=>r.id===id))||tune.region;else if(!l.region_ids.includes(tune.region))return;
    e.preventDefault();e.stopPropagation();tune.level=id;map.dragging.disable();label.setPointerCapture(e.pointerId);
    const a=annotations[id]||{};dragLabel={label,id,pointer:e.pointerId,x:e.clientX,y:e.clientY,left:parseFloat(label.style.left),top:parseFloat(label.style.top),sx:a.labelShiftX||0,sy:a.labelShiftY||0};
  },true);
  container.addEventListener('pointermove',e=>{if(!dragLabel)return;const d=dragLabel;d.dx=clamp(e.clientX-d.x,-200-d.sx,200-d.sx,0);d.dy=clamp(e.clientY-d.y,-200-d.sy,200-d.sy,0);d.label.style.left=`${d.left+d.dx}px`;d.label.style.top=`${d.top+d.dy}px`});
  const end=()=>{if(!dragLabel)return;const d=dragLabel;dragLabel=null;annotations[d.id]={...annotations[d.id],labelShiftX:d.sx+(d.dx||0),labelShiftY:d.sy+(d.dy||0)};if(d.label.hasPointerCapture(d.pointer))d.label.releasePointerCapture(d.pointer);map.dragging.enable();saveEditorial();drawRegions();drawMarkers();renderTunePanel();requestLabelPlacement()};
  container.addEventListener('pointerup',end);container.addEventListener('pointercancel',end);
  container.addEventListener('click',e=>{if(tune.active&&e.target.closest('[data-drag-level]')){e.stopPropagation();e.preventDefault()}},true);
  drawAnnotations();requestLabelPlacement();
}

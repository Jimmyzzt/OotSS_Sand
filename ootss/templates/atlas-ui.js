/* Prefixes stay outside the ordinal box so the ordinal anchor never moves. */
const atlasCompletionSets=new WeakMap();
globalThis.AtlasUI = {
  initialMap(worlds,query,lastMap){
    return worlds.find(m=>m.map_id===query.get('map'))||worlds.find(m=>m.levels.some(l=>l.level_id===query.get('level')))||worlds.find(m=>m.parts.some(p=>String(p.part)===query.get('p')))||worlds.find(m=>m.map_id===lastMap)||worlds[0];
  },
  mapGeometry(data){
    const [left,bottom,right,top]=data.bounds||[-24.5,-18.5,165.5,170.5],factor=512/190;
    return {bounds:[[bottom,left],[top,right]],center:[(bottom+top)/2,(left+right)/2],transform:[factor,-left*factor,-factor,top*factor]};
  },
  gridBounds(data){return data.grid?.bounds||[-24.5,-2.5,165.5,153.5];},
  tileAvailable(coords,coverage){
    return coords.x>=0&&coords.y>=0&&coords.x<2**coords.z&&coords.y<2**coords.z&&(!coverage||coverage.has(`${coords.y}/${coords.x}`));
  },
  completed(levels,save,id,saveId=id){
    if(!save)return levels[id]?.completed===true;
    let solved=atlasCompletionSets.get(save.solved);if(!solved){solved=new Set(save.solved);atlasCompletionSets.set(save.solved,solved)}
    return solved.has(saveId)?save.overrides[id]!==false:levels[id]?.completed===true;
  },
  newSaveProgress(solved,source,readAt){return {version:1,source:source.slice(0,300),readAt,solved:[...new Set(solved)],overrides:{}};},
  parseSaveProgress(value,levelIds){
    if(value===null)return null;
    if(!value||value.version!==1||!Array.isArray(value.solved)||value.solved.length>50000||typeof value.source!=='string'||typeof value.readAt!=='string'||!Number.isFinite(Date.parse(value.readAt)))throw Error('不是有效的存档完成记录');
    const solved=[...new Set(value.solved.filter(id=>typeof id==='string'&&levelIds.has(id)))],overrides=Object.create(null);
    for(const [id,flag] of Object.entries(value.overrides||{}))if(levelIds.has(id)&&flag===false)overrides[id]=false;
    return {version:1,source:value.source.slice(0,300),readAt:new Date(value.readAt).toISOString(),solved,overrides};
  },
  manualCompletion(levels,save,id,completed,saveId=id){
    const next={...levels,[id]:{...levels[id],completed}};
    if(!save)return {levels:next,saveProgress:null};
    const overrides={...save.overrides};if(save.solved.includes(saveId)&&!completed)overrides[id]=false;else delete overrides[id];
    return {levels:next,saveProgress:{...save,overrides}};
  },
  includesRegion(level,state,forMap=false) {
    return !state.region || (forMap && Boolean(state.part)) || level.region_ids.includes(state.region);
  },
  includesCompletion(completed,showCompleted=true) {return showCompleted || !completed;},
  inViewport(xy,bounds,focused=false) {
    return focused || !bounds || (xy[0]>=bounds.west && xy[0]<=bounds.east && xy[1]>=bounds.south && xy[1]<=bounds.north);
  },
  coincidentOffsets(points,sizeOf=p=>p.size) {
    const groups=new Map(),offsets=new Map();
    for(const point of points){const key=JSON.stringify([point.x,point.y]);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(point)}
    for(const group of groups.values()){
      if(new Set(group.map(p=>p.levelId)).size<2)continue;
      const sorted=[...group].sort((a,b)=>(b.priority||0)-(a.priority||0)||a.key.localeCompare(b.key));
      const anchorSize=sizeOf(sorted[0]);
      for(let i=1;i<sorted.length;i++){
        const point=sorted[i],size=sizeOf(point),ring=1+Math.floor((i-1)/8),angle=Math.PI/4+(i-1)%8*Math.PI/4;
        const distance=((anchorSize+size)/2+24)*ring;
        offsets.set(point.key,{x:Math.round(Math.cos(angle)*distance),y:Math.round(Math.sin(angle)*distance),anchorSize});
      }
    }
    return offsets;
  },
  leaderPath(offset,size) {
    if(!offset)return '';
    const length=Math.hypot(offset.x,offset.y);if(length<1)return '';
    const ux=-offset.x/length,uy=-offset.y/length,c=size/2;
    const sx=c+ux*(size/2+3),sy=c+uy*(size/2+3),ex=c-offset.x-ux*(offset.anchorSize/2+4),ey=c-offset.y-uy*(offset.anchorSize/2+4);
    return `M${sx},${sy} L${ex},${ey} M${ex-ux*6-uy*3},${ey-uy*6+ux*3} L${ex},${ey} L${ex-ux*6+uy*3},${ey-uy*6-ux*3}`;
  },
  parseEditorial(data, levelIds, regionKeys) {
    if (!data || ![1,2,3].includes(data.version) || !data.levels || typeof data.levels !== 'object' || Array.isArray(data.levels)) throw Error('不是有效的标注文件');
    const levels = Object.create(null), regions = Object.create(null);
    for (const [id,v] of Object.entries(data.levels)) {
      if (!levelIds.has(id) || !v || typeof v !== 'object' || Array.isArray(v)) continue;
      const r = {};
      for (const k of ['big_star','multi_save','completed']) if (typeof v[k] === 'boolean') r[k] = v[k];
      if (typeof v.notes === 'string') r.notes = v.notes.slice(0,200);
      if (typeof v.labelHidden === 'boolean') r.labelHidden = v.labelHidden;
      if (AtlasUI.positions.includes(v.labelPosition)) r.labelPosition = v.labelPosition;
      for (const k of ['labelShiftX','labelShiftY']) if (Number.isFinite(v[k])) r[k] = Math.max(-200,Math.min(200,v[k]));
      levels[id] = r;
    }
    if (data.regions && typeof data.regions === 'object' && !Array.isArray(data.regions)) {
      for (const [id,v] of Object.entries(data.regions)) {
        if (!regionKeys.has(id) || !v || typeof v !== 'object' || Array.isArray(v)) continue;
        const r = {};
        if (typeof v.title === 'string' && v.title.trim()) r.title = v.title.trim().slice(0,80);
        if (AtlasUI.positions.includes(v.labelPosition)) r.labelPosition = v.labelPosition;
        if (v.style && typeof v.style === 'object') r.style = AtlasUI.mapStyle(v.style);
        if (Array.isArray(v.texts)) r.texts = v.texts.slice(0,100).flatMap((t,i)=>{
          if (!t || typeof t.text !== 'string' || !t.text.trim() || !Number.isFinite(t.x) || !Number.isFinite(t.y) || t.x < -25 || t.x > 171 || t.y < -25 || t.y > 171) return [];
          return [{id:`text-${i}`,text:t.text.slice(0,300),x:t.x,y:t.y,...AtlasUI.textStyle(t)}];
        });
        regions[id] = r;
      }
    }
    const style = data.style && typeof data.style === 'object' ? AtlasUI.readerStyle(data.style) : {};
    return {levels,regions,style,...(Object.hasOwn(data,'saveProgress')?{saveProgress:AtlasUI.parseSaveProgress(data.saveProgress,levelIds)}:{})};
  },
  positions:['bottom-left','top-left','top-right','bottom-right','top-center','bottom-center','middle-left','middle-right','middle-center'],
  textStyle(v={}) {
    const number=(n,min,max,d)=>Number.isFinite(n)?Math.max(min,Math.min(max,n)):d;
    const color=(s,d)=>/^#[0-9a-f]{6}$/i.test(s)?s:d;
    return {size:number(v.size,10,72,22),color:color(v.color,'#fff6a8'),strokeWidth:number(v.strokeWidth,0,8,2),strokeColor:color(v.strokeColor,'#17211c')};
  },
  readerStyle(v={}) {
    const r={};
    for (const [k,min,max] of [['point',.6,2.6],['regionLabel',10,42],['levelLabel',10,42],['offsetX',0,80],['offsetY',0,80],['completedOpacity',.1,1]]) if(Number.isFinite(v[k])) r[k]=Math.max(min,Math.min(max,v[k]));
    for(const k of ['regionPosition','levelPosition']) if(AtlasUI.positions.includes(v[k])) r[k]=v[k];
    for(const k of ['regionLabels','levelLabels','adaptPositions','showCompleted']) if(typeof v[k]==='boolean')r[k]=v[k];
    return r;
  },
  defaults:{point:1.6,regionLabel:18,levelLabel:18,regionPosition:'bottom-left',levelPosition:'top-right',offsetX:5,offsetY:4,completedOpacity:.35},
  mapStyle(v={}) {
    const s=AtlasUI.readerStyle(v);
    return Object.fromEntries(Object.keys(AtlasUI.defaults).filter(k=>k!=='completedOpacity'&&k in s).map(k=>[k,s[k]]));
  },
  adaptiveEnabled(prefs,state) {return Boolean(prefs.regionLabels&&prefs.adaptPositions&&(state.part||state.region));},
  resetMapStyles(levels,regions,{clearCompletion=false}={}) {
    const clone=structuredClone({levels,regions});
    for(const r of Object.values(clone.levels)) for(const k of ['labelHidden','labelPosition','labelShiftX','labelShiftY'])delete r[k];
    if(clearCompletion)for(const r of Object.values(clone.levels))delete r.completed;
    for(const r of Object.values(clone.regions)) {
      delete r.style;delete r.labelPosition;
    }
    return clone;
  },
  editHistory(limit=60) {
    const past=[],future=[];let group=null,last=0;
    return {
      record(state,key,now=Date.now()) {
        if(!key||key!==group||now-last>700){past.push(structuredClone(state));if(past.length>limit)past.shift();}
        future.length=0;group=key;last=now;
      },
      undo(state) {if(!past.length)return null;future.push(structuredClone(state));group=null;return past.pop();},
      redo(state) {if(!future.length)return null;past.push(structuredClone(state));group=null;return future.pop();},
      get canUndo(){return past.length>0},get canRedo(){return future.length>0}
    };
  },
  labelRect(bounds,size,position,padding=5) {
    const [vertical,horizontal]=position.split('-');
    const x=horizontal==='left'?bounds.left+padding:horizontal==='right'?bounds.right-size.width-padding:(bounds.left+bounds.right-size.width)/2;
    const y=vertical==='top'?bounds.top+padding:vertical==='bottom'?bounds.bottom-size.height-padding:(bounds.top+bounds.bottom-size.height)/2;
    return {left:x,top:y,right:x+size.width,bottom:y+size.height};
  },
  chooseRegionPosition(bounds,size,obstacles,preferred='bottom-left') {
    const order=[preferred,...AtlasUI.positions.slice(1),'bottom-left'];
    for (const position of new Set(order)) {
      const r=AtlasUI.labelRect(bounds,size,position);
      if (r.left < bounds.left || r.right > bounds.right || r.top < bounds.top || r.bottom > bounds.bottom) continue;
      if (!obstacles.some(o=>r.left < o.right+3 && r.right > o.left-3 && r.top < o.bottom+3 && r.bottom > o.top-3)) return position;
    }
    return 'bottom-left';
  },
  levelLabelStyle(position,offsetX,offsetY,shiftX=0,shiftY=0) {
    const [vertical,horizontal]=position.split('-');
    const x=(horizontal==='left'?-offsetX:horizontal==='right'?offsetX:0)+shiftX;
    const y=(vertical==='top'?-offsetY:vertical==='bottom'?offsetY:0)+shiftY;
    return {x,y,tx:horizontal==='left'?-100:horizontal==='right'?0:-50,ty:vertical==='top'?-100:vertical==='bottom'?0:-50};
  },
  markerRadius(big, scale, zoom) {
    return Math.max((big ? 6.75 : 4.5) * scale, Math.min(42, (big ? 9 : 6) * scale * 2 ** (zoom - 2.75)));
  },
  markerLabels(levels, selectedPart, displayPart = p => p) {
    return new Map(levels.map(level => {
      const visit = level.shown[0], ordinal = String(visit.ordinal), prefix = selectedPart ? '' : `${displayPart(visit.part)}·`;
      return [level.level_id, {text:prefix + ordinal, ordinal, prefix, part:visit.part, withPart:!selectedPart}];
    }));
  }
};

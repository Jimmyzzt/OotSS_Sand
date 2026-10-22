/* Prefixes stay outside the ordinal box so the ordinal anchor never moves. */
globalThis.AtlasUI = {
  includesRegion(level,state,forMap=false) {
    return !state.region || (forMap && Boolean(state.part)) || level.region_ids.includes(state.region);
  },
  inViewport(xy,bounds,focused=false) {
    return focused || !bounds || (xy[0]>=bounds.west && xy[0]<=bounds.east && xy[1]>=bounds.south && xy[1]<=bounds.north);
  },
  parseEditorial(data, levelIds, regionKeys) {
    if (!data || ![1,2,3].includes(data.version) || !data.levels || typeof data.levels !== 'object' || Array.isArray(data.levels)) throw Error('不是有效的标注文件');
    const levels = Object.create(null), regions = Object.create(null);
    for (const [id,v] of Object.entries(data.levels)) {
      if (!levelIds.has(id) || !v || typeof v !== 'object' || Array.isArray(v)) continue;
      const r = {};
      for (const k of ['big_star','multi_save']) if (typeof v[k] === 'boolean') r[k] = v[k];
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
    return {levels,regions,style};
  },
  positions:['bottom-left','top-left','top-right','bottom-right','top-center','bottom-center','middle-left','middle-right','middle-center'],
  textStyle(v={}) {
    const number=(n,min,max,d)=>Number.isFinite(n)?Math.max(min,Math.min(max,n)):d;
    const color=(s,d)=>/^#[0-9a-f]{6}$/i.test(s)?s:d;
    return {size:number(v.size,10,72,22),color:color(v.color,'#fff6a8'),strokeWidth:number(v.strokeWidth,0,8,2),strokeColor:color(v.strokeColor,'#17211c')};
  },
  readerStyle(v={}) {
    const r={};
    for (const [k,min,max] of [['point',.6,2.6],['regionLabel',10,42],['levelLabel',10,42],['offsetX',0,80],['offsetY',0,80]]) if(Number.isFinite(v[k])) r[k]=Math.max(min,Math.min(max,v[k]));
    for(const k of ['regionPosition','levelPosition']) if(AtlasUI.positions.includes(v[k])) r[k]=v[k];
    for(const k of ['regionLabels','levelLabels','adaptPositions','customTexts']) if(typeof v[k]==='boolean')r[k]=v[k];
    return r;
  },
  defaults:{point:1.6,regionLabel:18,levelLabel:18,regionPosition:'bottom-left',levelPosition:'top-right',offsetX:5,offsetY:4},
  mapStyle(v={}) {
    const s=AtlasUI.readerStyle(v);
    return Object.fromEntries(Object.keys(AtlasUI.defaults).filter(k=>k in s).map(k=>[k,s[k]]));
  },
  adaptiveEnabled(prefs,state) {return Boolean(prefs.regionLabels&&prefs.adaptPositions&&(state.part||state.region));},
  resetMapStyles(levels,regions) {
    const clone=structuredClone({levels,regions});
    for(const r of Object.values(clone.levels)) for(const k of ['labelHidden','labelPosition','labelShiftX','labelShiftY'])delete r[k];
    for(const r of Object.values(clone.regions)) {
      delete r.style;delete r.labelPosition;
      if(Array.isArray(r.texts))r.texts=r.texts.map(t=>({...t,...AtlasUI.textStyle({size:AtlasUI.defaults.regionLabel})}));
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

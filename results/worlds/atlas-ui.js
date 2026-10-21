/* Prefixes stay outside the ordinal box so the ordinal anchor never moves. */
globalThis.AtlasUI = {
  parseEditorial(data, levelIds, regionKeys) {
    if (!data || ![1,2,3].includes(data.version) || !data.levels || typeof data.levels !== 'object' || Array.isArray(data.levels)) throw Error('不是有效的标注文件');
    const levels = Object.create(null), regions = Object.create(null);
    for (const [id,v] of Object.entries(data.levels)) {
      if (!levelIds.has(id) || !v || typeof v !== 'object' || Array.isArray(v)) continue;
      const r = {};
      for (const k of ['big_star','multi_save']) if (typeof v[k] === 'boolean') r[k] = v[k];
      if (typeof v.notes === 'string') r.notes = v.notes.slice(0,200);
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
    for(const k of ['regionLabels','levelLabels']) if(typeof v[k]==='boolean')r[k]=v[k];
    return r;
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

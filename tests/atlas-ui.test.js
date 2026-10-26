import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import '../ootss/templates/atlas-ui.js';
const {markerLabels,markerRadius}=globalThis.AtlasUI;
const level=(id,ordinal,x,part=2,region='mixed')=>({level_id:id,shown:[{part,ordinal}],region_ids:[region],entries:[{coordinates:[x,0]}]});
test('only identical coordinates of distinct levels are spread, retaining the star at its true position',()=>{
  const points=[{key:'normal',levelId:'a',x:54,y:110,size:24},{key:'star',levelId:'b',x:54,y:110,size:36,priority:1},{key:'near',levelId:'c',x:54.0001,y:110,size:24}];
  const original=structuredClone(points),offsets=AtlasUI.coincidentOffsets(points);
  assert.deepEqual([...offsets.keys()],['normal']);
  assert.ok(offsets.get('normal').x>0&&offsets.get('normal').y>0);
  assert.ok(Math.hypot(offsets.get('normal').x,offsets.get('normal').y)>(24+36)/2);
  assert.deepEqual([...AtlasUI.coincidentOffsets([...points].reverse())], [...offsets]);
  assert.deepEqual(points,original);
  assert.equal(AtlasUI.coincidentOffsets([points[0],{...points[0],key:'same-level'}]).size,0);
});
test('the reported sky pair receives exactly one leader, and filtering to one level removes it',()=>{
  const data=JSON.parse(readFileSync(new URL('../results/worlds/index.json',import.meta.url),'utf8'));
  for(const map of data.maps){
    const points=map.levels.flatMap(l=>l.entries.map((e,i)=>({key:JSON.stringify([l.level_id,i]),levelId:l.level_id,x:e.coordinates[0],y:e.coordinates[1],size:l.tags.big_star?36:24,priority:l.tags.big_star?1:0})));
    const offsets=AtlasUI.coincidentOffsets(points);
    assert.deepEqual([...offsets.keys()],map.map_id==='sky'?['["sky_druid_kill",0]']:[]);
    assert.equal(AtlasUI.coincidentOffsets(points.filter(p=>p.levelId==='sky_druid_kill')).size,0);
  }
});
test('leaders stop outside the real pin and do not exist for an unmoved marker',()=>{
  assert.equal(AtlasUI.leaderPath(null,24),'');
  const path=AtlasUI.leaderPath({x:38,y:38,anchorSize:36},24);
  assert.ok(!path.includes('NaN'));
  const points=path.match(/-?\d+(?:\.\d+)?/g).map(Number),end={x:points[2],y:points[3]};
  assert.ok(Math.abs(Math.hypot(end.x-(12-38),end.y-(12-38))-22)<.001);
});
test('a part keeps neighboring-region markers while its sidebar follows the selected region',()=>{
  const other=level('a',1,0,9,'neighbor'),state={part:9,region:'selected'};
  assert.equal(AtlasUI.includesRegion(other,state,true),true);
  assert.equal(AtlasUI.includesRegion(other,state),false);
  assert.equal(AtlasUI.includesRegion(other,{...state,part:0},true),false);
  assert.equal(AtlasUI.includesRegion(other,{...state,region:null}),true);
});
test('viewport culling retains boundary markers and a focused offscreen entry',()=>{
  const bounds={west:0,east:10,south:0,north:10};
  assert.equal(AtlasUI.inViewport([0,10],bounds),true);
  assert.equal(AtlasUI.inViewport([11,5],bounds),false);
  assert.equal(AtlasUI.inViewport([11,5],bounds,true),true);
  assert.equal(AtlasUI.inViewport([100,100],null),true);
});
test('all-parts labels always show a separate prefix, including adjacent and single-part regions',()=>{
  const levels=[level('a',1,0),level('b',2,1),level('c',3,2),level('e',29,1,4),level('f',5,0,2,'single')];
  const labels=markerLabels(levels,0);
  assert.deepEqual(levels.map(l=>labels.get(l.level_id).text),['2·1','2·2','2·3','4·29','2·5']);
  assert.deepEqual(levels.map(l=>labels.get(l.level_id).ordinal),['1','2','3','29','5']);
  assert.deepEqual(levels.map(l=>markerLabels(levels,2).get(l.level_id).prefix),['','','','','']);
});

test('prefixes follow remapped display parts without changing the ordinal',()=>{
  const labels=markerLabels([level('b',2,1),level('a',1,0)],0,p=>p+1);
  assert.equal(labels.get('a').prefix,'3·');
  assert.equal(labels.get('a').ordinal,'1');
  assert.equal(labels.get('b').text,'3·2');
});

test('marker size follows zoom and reader scale, with usable overview and bounded close-up sizes',()=>{
  assert.equal(markerRadius(false,1.6,3)*2,markerRadius(false,1.6,4));
  assert.ok(markerRadius(false,1.6,-1)>=5);
  assert.ok(markerRadius(true,1.6,3)>markerRadius(false,1.6,3));
  assert.equal(markerRadius(false,.8,3)*2,markerRadius(false,1.6,3));
  assert.equal(markerRadius(false,2.6,7),42);
});
test('published hero cell retains P2 and P4 prefixes on every ordinal',()=>{
  const data=JSON.parse(readFileSync(new URL('../results/stage1/index.json',import.meta.url),'utf8'));
  const r=data.regions.find(r=>r.title==='搬运英雄1');
  const levels=data.levels.filter(l=>l.region_ids.includes(r.id)).map(l=>({...l,shown:l.visits}));
  const labels=markerLabels(levels,0);
  assert.equal(labels.get('heroes1_1').text,'2·1');
  assert.equal(labels.get('heroes1_2_v2').text,'2·2');
  assert.equal(labels.get('victory_lap').text,'4·29');
  assert.equal(new Set([...labels.values()].map(v=>v.part)).size,2);
});

test('editorial import keeps legacy flags and validates named regions without prototype keys',()=>{
  const ids=new Set(['mirror_1']),keys=new Set(['overworld:1,0']);
  const old=AtlasUI.parseEditorial({version:1,levels:{mirror_1:{multi_save:true,notes:'旧标注'}}},ids,keys);
  assert.equal(old.levels.mirror_1.multi_save,true);
  const next=AtlasUI.parseEditorial({version:2,levels:{mirror_1:{big_star:false},bad:{notes:'skip'}},regions:{'overworld:1,0':{title:'  镜之群岛  '},unknown:{title:'skip'}}},ids,keys);
  assert.deepEqual(Object.keys(next.levels),['mirror_1']);
  assert.deepEqual({...next.regions},{'overworld:1,0':{title:'镜之群岛'}});
  assert.throws(()=>AtlasUI.parseEditorial({version:2,levels:[]},ids,keys));
});

test('region labels try the requested corner then the specified collision fallback order',()=>{
  const bounds={left:0,top:0,right:300,bottom:300},size={width:30,height:20};
  const blocked=[];
  for(const position of AtlasUI.positions){
    assert.equal(AtlasUI.chooseRegionPosition(bounds,size,blocked),position);
    blocked.push(AtlasUI.labelRect(bounds,size,position));
  }
  assert.equal(AtlasUI.chooseRegionPosition(bounds,size,blocked,'top-right'),'bottom-left');
  assert.equal(AtlasUI.chooseRegionPosition(bounds,size,[],'middle-center'),'middle-center');
});

test('level label direction and per-level shifts keep the existing default ordinal anchor',()=>{
  assert.deepEqual(AtlasUI.levelLabelStyle('top-right',5,4),{x:5,y:-4,tx:0,ty:-100});
  assert.deepEqual(AtlasUI.levelLabelStyle('bottom-center',12,9,7,-3),{x:7,y:6,tx:-50,ty:0});
  assert.deepEqual(AtlasUI.levelLabelStyle('middle-left',12,9),{x:-12,y:0,tx:-100,ty:-50});
});

test('v3 import preserves map editing and clamps untrusted text/style fields',()=>{
  const source={version:3,levels:{a:{big_star:true,labelPosition:'bottom-left',labelShiftX:900}},regions:{r:{title:' 区域 ',labelPosition:'top-right',texts:[{text:'<b>注释</b>',x:10,y:20,size:100,strokeWidth:99,color:'red;display:none',strokeColor:'#112233'},{text:'outside',x:999,y:0}]}},style:{regionLabel:22,levelLabel:16,regionPosition:'top-left',point:1.8,offsetX:900,theme:'injected'}};
  const parsed=AtlasUI.parseEditorial(source,new Set(['a']),new Set(['r']));
  assert.equal(parsed.levels.a.labelShiftX,200);
  assert.equal(parsed.regions.r.texts.length,1);
  assert.equal(parsed.regions.r.texts[0].text,'<b>注释</b>');
  assert.deepEqual(AtlasUI.textStyle(parsed.regions.r.texts[0]),{size:72,color:'#fff6a8',strokeWidth:8,strokeColor:'#112233'});
  assert.deepEqual(parsed.style,{point:1.8,regionLabel:22,levelLabel:16,offsetX:80,regionPosition:'top-left'});
});

test('position adaptation runs only for a filtered view and can be switched off',()=>{
  const prefs={regionLabels:true,adaptPositions:true};
  assert.equal(AtlasUI.adaptiveEnabled(prefs,{part:0,region:null}),false);
  assert.equal(AtlasUI.adaptiveEnabled(prefs,{part:19,region:null}),true);
  assert.equal(AtlasUI.adaptiveEnabled(prefs,{part:0,region:'r'}),true);
  assert.equal(AtlasUI.adaptiveEnabled({...prefs,adaptPositions:false},{part:19}),false);
});

test('bounded edit history coalesces typing, supports redo, and discards a diverged redo branch',()=>{
  const h=AtlasUI.editHistory(2),initial={title:'a'};
  h.record(initial,'typing',100);initial.title='b';h.record(initial,'typing',200);
  assert.deepEqual(h.undo({title:'c'}),{title:'a'});
  assert.deepEqual(h.redo({title:'a'}),{title:'c'});
  h.undo({title:'c'});h.record({title:'a'},'new',300);
  assert.equal(h.canRedo,false);
  h.record({title:'d'},null,400);h.record({title:'e'},null,500);
  assert.deepEqual(h.undo({title:'f'}),{title:'e'});
  assert.deepEqual(h.undo({title:'e'}),{title:'d'});
  assert.equal(h.undo({title:'d'}),null);
});

test('resetting map styles restores labels while preserving annotation meaning and text locations',()=>{
  const levels={a:{big_star:true,notes:'保留',labelHidden:true,labelShiftX:40,labelPosition:'top-left'}};
  const regions={r:{title:'区域名',labelPosition:'top-right',style:{point:2.4},texts:[{id:'a',text:'说明',x:10,y:20,size:40,color:'#ffffff',strokeWidth:4,strokeColor:'#000000'}]}};
  const reset=AtlasUI.resetMapStyles(levels,regions);
  assert.deepEqual(reset.levels.a,{big_star:true,notes:'保留'});
  assert.equal(reset.regions.r.title,'区域名');
  assert.equal(reset.regions.r.style,undefined);
  assert.deepEqual(reset.regions.r.texts[0],{id:'a',text:'说明',x:10,y:20,...AtlasUI.textStyle({size:18})});
  assert.equal(levels.a.labelHidden,true);
});

test('hidden labels and isolated region styles survive editorial import without global switches leaking in',()=>{
  const p=AtlasUI.parseEditorial({version:3,levels:{a:{labelHidden:true}},regions:{r:{style:{point:2.4,regionLabel:24,adaptPositions:false}}}},new Set(['a']),new Set(['r']));
  assert.equal(p.levels.a.labelHidden,true);
  assert.deepEqual(p.regions.r.style,{point:2.4,regionLabel:24});
  const regionStyle={...AtlasUI.defaults,...p.regions.r.style};
  assert.equal(regionStyle.regionLabel,24);
  assert.equal(regionStyle.offsetY,4);
});

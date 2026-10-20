import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import '../ootss/templates/atlas-ui.js';
const {markerLabels,markerRadius}=globalThis.AtlasUI;
const level=(id,ordinal,x,part=2,region='mixed')=>({level_id:id,shown:[{part,ordinal}],region_ids:[region],entries:[{coordinates:[x,0]}]});
const regions=new Map([['mixed',{id:'mixed',parts:[2,4]}],['single',{id:'single',parts:[2]}]]);
test('nearby ordinal runs share one prefix; distant runs and other parts retain theirs',()=>{
  const levels=[level('a',1,0),level('b',2,1),level('c',3,2),level('d',4,12),level('e',29,1,4),level('f',5,0,2,'single')];
  const labels=markerLabels(levels,0,regions);
  assert.deepEqual(levels.map(l=>labels.get(l.level_id).text),['2·1','2','3','2·4','4·29','5']);
  assert.equal(labels.get('a').mixed,true);
  assert.equal(labels.get('f').mixed,false);
  assert.deepEqual(levels.map(l=>markerLabels(levels,2,regions).get(l.level_id).text),['1','2','3','4','29','5']);
});
test('prefixes follow remapped display parts and remain stable under shuffled input',()=>{
  const labels=markerLabels([level('b',2,1),level('a',1,0)],0,regions,p=>p+1);
  assert.equal(labels.get('a').text,'3·1');
  assert.equal(labels.get('b').text,'2');
});
test('marker size follows zoom and reader scale, with usable overview and bounded close-up sizes',()=>{
  assert.equal(markerRadius(false,1.6,3)*2,markerRadius(false,1.6,4));
  assert.ok(markerRadius(false,1.6,-1)>=5);
  assert.ok(markerRadius(true,1.6,3)>markerRadius(false,1.6,3));
  assert.equal(markerRadius(false,.8,3)*2,markerRadius(false,1.6,3));
  assert.equal(markerRadius(false,2.6,7),42);
});
test('published mixed hero cell retains P2 and P4 identities without repeating every prefix',()=>{
  const data=JSON.parse(readFileSync(new URL('../results/stage1/index.json',import.meta.url),'utf8'));
  const r=data.regions.find(r=>r.title==='搬运英雄1');
  const levels=data.levels.filter(l=>l.region_ids.includes(r.id)).map(l=>({...l,shown:l.visits}));
  const labels=markerLabels(levels,0,new Map(data.regions.map(r=>[r.id,r])));
  assert.equal(labels.get('heroes1_1').text,'2·1');
  assert.equal(labels.get('heroes1_2_v2').text,'2');
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

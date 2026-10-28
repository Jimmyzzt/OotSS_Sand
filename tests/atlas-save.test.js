import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdirSync,writeFileSync,readFileSync} from 'node:fs';
import {createContext,runInContext} from 'node:vm';
import '../ootss/templates/atlas-save.js';
import '../ootss/templates/atlas-ui.js';

test('intro aliases read the original save ID but retain independent manual overrides',()=>{
 const save=AtlasUI.newSaveProgress(['heroes1_7_v2'],'slot','2026-10-28T00:00:00Z');
 assert.equal(AtlasUI.completed({},save,'intro-heroes1_7_v2','heroes1_7_v2'),true);
 const manual=AtlasUI.manualCompletion({},save,'intro-heroes1_7_v2',false,'heroes1_7_v2');
 const parsed=AtlasUI.parseSaveProgress(manual.saveProgress,new Set(['heroes1_7_v2','intro-heroes1_7_v2']));
 assert.equal(AtlasUI.completed(manual.levels,parsed,'intro-heroes1_7_v2','heroes1_7_v2'),false);
 assert.equal(AtlasUI.completed(manual.levels,parsed,'heroes1_7_v2'),true);
 assert.equal(AtlasUI.completed(manual.levels,null,'intro-heroes1_7_v2','heroes1_7_v2'),false);
});

// Binary fixtures derived from the documented version gates, with nonzero legacy
// padding so accidental reads from removed fields do not look like empty tables.
function statusFixture(version,levels=[['solved',1],['partial',2],['entered',4],['both',3]]){
 const chunks=[];
 const u8=value=>{chunks.push(Buffer.from([value]));},u32=value=>{const b=Buffer.alloc(4);b.writeUInt32LE(value);chunks.push(b)},pad=(length,value=0)=>chunks.push(Buffer.alloc(length,value));
 const text=value=>{const b=Buffer.from(value),n=Buffer.alloc(2);n.writeUInt16LE(b.length);chunks.push(n,b)};
 u32(version);if(version>=30)u32(7);if(version>=12)pad(16,0x11);
 if(version>=19){u8(3);pad(16,0x22);if(version>=22)pad(8,0x33);if(version>=27)u32(2)}
 u32(200);u32(201);if(version<=25)pad(4,0xee);
 for(const n of version>=8?[2,3,4,5,6,7,8,9]:[2,3,4,5,8,9])u32(200+n);
 if(version>=13)pad(8,0x44);if(version>=9)u32(42);if(version>=11)u32(3);if(version>=19)u32(4);if(version>=20)u32(5);
 if(version>=16)u8(1);if(version>=24)u8(1);if(version>=23&&version<=31)pad(33,0xee);if(version>=17&&version<=20)pad(version===17?8:9,0xee);
 if(version<=24)text('legacy');text('current');if(version>=33)text('menu');
 u32(levels.length);for(const [name,flags]of levels){text(name);u8(flags)}
 return Buffer.concat(chunks);
}

test('all supported Status versions read SOLVED only, not partial or entered flags',()=>{
 for(let version=5;version<=33;version++)assert.deepEqual(AtlasSave.parse(statusFixture(version)),{version,solved:['solved','both']});
});

test('binary views honor byte offsets and duplicate IDs do not inflate completion',()=>{
 const bytes=statusFixture(33,[['heroes1_1',1],['heroes1_1',9],['druid_3d_beam',2]]),wrapped=Buffer.concat([Buffer.alloc(7),bytes,Buffer.alloc(9)]);
 assert.deepEqual(AtlasSave.parse(wrapped.subarray(7,7+bytes.length)).solved,['heroes1_1']);
 assert.deepEqual(AtlasSave.parse(statusFixture(33,[])).solved,[]);
});

test('truncated prefixes, corrupt counts, invalid strings and unsupported versions are rejected',()=>{
 const file=statusFixture(33);
 for(let length=0;length<file.length;length++)assert.throws(()=>AtlasSave.parse(file.subarray(0,length)));
 for(const version of [0,4,34,0xffffffff]){const bytes=Buffer.alloc(4);bytes.writeUInt32LE(version);assert.throws(()=>AtlasSave.parse(bytes),/版本/)}
 const badCount=statusFixture(33,[]);badCount.writeUInt32LE(0xffffffff,badCount.length-4);assert.throws(()=>AtlasSave.parse(badCount),/列表/);
 const badText=statusFixture(33,[['x',1]]);badText[badText.length-2]=0xff;assert.throws(()=>AtlasSave.parse(badText));
 assert.throws(()=>AtlasSave.parse(new Uint8Array(AtlasSave.maxBytes+1)),/过大/);
});

test('only Status files are offered and campaigns remain distinct',()=>{
 const files=[{name:'overworld.history'},{name:'Status.sokoban_status',webkitRelativePath:'root/b/Status.sokoban_status'},{name:'_temp_Status.sokoban_status'},{name:'Status.sokoban_status',webkitRelativePath:'root/a/Status.sokoban_status'}];
 assert.deepEqual(AtlasSave.statusFiles(files).map(f=>f.webkitRelativePath),['root/a/Status.sokoban_status','root/b/Status.sokoban_status']);
});

test('directory discovery only lists Status handles without opening histories or combining campaigns',async()=>{
 const file={kind:'file',getFile(){throw Error('discovery must not read file bodies')}},folder=(name,children)=>({kind:'directory',name,async *entries(){yield*children}});
 const root=folder('Game',[['overworld.history',file],['a',folder('a',[['Status.sokoban_status',file]])],['b',folder('b',[['Status.sokoban_status',file],['_temp_Status.sokoban_status',file]])]]);
 const found=await AtlasSave.findStatuses(root);assert.deepEqual(found.map(f=>f.path),['Game/a/Status.sokoban_status','Game/b/Status.sokoban_status']);
 const oversized={kind:'directory',name:'large',async *entries(){for(let i=0;i<20001;i++)yield['file'+i,file]}};
 await assert.rejects(AtlasSave.findStatuses(oversized),/过多/);
});

test('each read wins over old manual false, additional manual true survives, detach restores manual results',()=>{
 const levels={a:{completed:false,big_star:true},extra:{completed:true},untouched:{notes:'keep'}};
 let save=AtlasUI.newSaveProgress(['a','b'],'slot/Status.sokoban_status','2026-10-27T10:00:00.000Z');
 assert.equal(AtlasUI.completed(levels,save,'a'),true);assert.equal(AtlasUI.completed(levels,save,'b'),true);assert.equal(AtlasUI.completed(levels,save,'extra'),true);
 const manual=AtlasUI.manualCompletion(levels,save,'a',false);
 assert.equal(AtlasUI.completed(manual.levels,manual.saveProgress,'a'),false);assert.equal(manual.saveProgress.overrides.a,false);
 save=AtlasUI.newSaveProgress(['a','b'],'slot/Status.sokoban_status','2026-10-27T10:01:00.000Z');
 assert.equal(AtlasUI.completed(manual.levels,save,'a'),true);
 assert.equal(AtlasUI.completed(manual.levels,null,'a'),false);assert.equal(AtlasUI.completed(manual.levels,null,'extra'),true);
 assert.equal(manual.levels.a.big_star,true);assert.equal(levels.a.completed,false);
});

test('manual positives remain independent of automatic membership and new reads replace the old save snapshot',()=>{
 let save=AtlasUI.newSaveProgress(['a'],'old','2026-10-27T10:00:00Z');
 const manual=AtlasUI.manualCompletion({},save,'a',true);
 assert.equal(AtlasUI.completed(manual.levels,null,'a'),true);
 save=AtlasUI.newSaveProgress(['b'],'new','2026-10-27T10:01:00Z');
 assert.equal(AtlasUI.completed({},save,'a'),false);assert.equal(AtlasUI.completed(manual.levels,save,'a'),true);assert.equal(AtlasUI.completed({},save,'b'),true);
});

test('backup distinguishes automatic, manual and post-read overrides; old backups do not detach a save',()=>{
 const ids=new Set(['a','extra']),save=AtlasUI.newSaveProgress(['a','outside'],'slot','2026-10-27T10:00:00Z');save.overrides={a:false,outside:false};
 const source={version:3,levels:{extra:{completed:true}},regions:{},saveProgress:save,style:{completedOpacity:.5}};
 const parsed=AtlasUI.parseEditorial(JSON.parse(JSON.stringify(source)),ids,new Set());
 assert.deepEqual(parsed.saveProgress.solved,['a']);assert.equal(parsed.saveProgress.overrides.a,false);assert.equal(AtlasUI.completed(parsed.levels,parsed.saveProgress,'a'),false);assert.equal(AtlasUI.completed(parsed.levels,parsed.saveProgress,'extra'),true);
 assert.equal(parsed.style.completedOpacity,.5);
 assert.equal(Object.hasOwn(AtlasUI.parseEditorial({version:3,levels:{}},ids,new Set()),'saveProgress'),false);
 assert.equal(AtlasUI.parseEditorial({version:3,levels:{},saveProgress:null},ids,new Set()).saveProgress,null);
 assert.throws(()=>AtlasUI.parseSaveProgress({version:1,solved:[],source:'bad',readAt:'invalid'},ids));
});

test('reset all clears manual completion without erasing other tags, and opacity cannot become unusable',()=>{
 const initial={a:{completed:true,notes:'keep',multi_save:true},b:{completed:false}};
 const reset=AtlasUI.resetMapStyles(initial,{}, {clearCompletion:true});
 assert.equal(reset.levels.a.completed,undefined);assert.equal(reset.levels.b.completed,undefined);assert.equal(reset.levels.a.notes,'keep');assert.equal(reset.levels.a.multi_save,true);
 assert.equal(AtlasUI.completed(reset.levels,null,'a'),false);
 assert.equal(AtlasUI.readerStyle({completedOpacity:0}).completedOpacity,.1);assert.equal(AtlasUI.readerStyle({completedOpacity:2}).completedOpacity,1);assert.equal(AtlasUI.mapStyle({completedOpacity:.5}).completedOpacity,undefined);
});

// Exercise the real dialog controller with replaceable on-disk file handles.
function saveDialogHarness({fallback=false}={}){
 const nodes=new Map();
 function element(){return {value:'',disabled:false,hidden:false,open:false,textContent:'',children:[],events:{},replaceChildren(){this.children=[];this.value=''},append(item){this.children.push(item);if(this.children.length===1)this.value=String(item.value)},addEventListener(type,handler){this.events[type]=handler},showModal(){this.open=true},close(){this.open=false;this.events.close?.()},click(){this.clicked=true}}}
 const $=id=>{if(!nodes.has(id))nodes.set(id,element());return nodes.get(id)};
 let bytes=statusFixture(33,[['a',1]]),permission='granted',pickerCalls=0,requests=0,fileReads=0,missing=false;
 const file=()=>({name:'Status.sokoban_status',size:bytes.length,arrayBuffer:async()=>bytes});
 const slots=['one','two'].map(name=>({kind:'directory',name,async *entries(){yield['Status.sokoban_status',{kind:'file',getFile(){throw Error('must resolve latest path')}}]},async getFileHandle(filename,options){assert.equal(filename,'Status.sokoban_status');assert.deepEqual({...options},{create:false});if(missing)throw new DOMException('missing','NotFoundError');return {async getFile(){fileReads++;return file()}}}}));
 const root={name:'Game',async *entries(){for(const slot of slots)yield[slot.name,slot]},async getDirectoryHandle(name,options){assert.deepEqual({...options},{create:false});return slots.find(slot=>slot.name===name)},async queryPermission(options){assert.equal(options.mode,'read');return permission},async requestPermission(options){assert.equal(options.mode,'read');requests++;permission='granted';return permission}};
 const context=createContext({$,TextDecoder,DOMException,Uint8Array,DataView,AtlasUI,worlds:[{levels:[{level_id:'a'},{level_id:'b'}]}],saveProgress:null,settings(){},document:{createElement:element},window:fallback?{}:{async showDirectoryPicker(options){assert.equal(options.mode,'read');pickerCalls++;return root}},remember(){},saveEditorial(){},map:{closePopup(){}},applyPrefs(){},render(){}});
 runInContext(readFileSync(new URL('../ootss/templates/atlas-save.js',import.meta.url),'utf8')+';initGameSaves();',context);
 return {$,context,file,setBytes(value){bytes=value},setPermission(value){permission=value},setMissing(){missing=true},get pickerCalls(){return pickerCalls},get requests(){return requests},get fileReads(){return fileReads}};
}

test('reopening retains the campaign and rereads replaced disk contents without choosing the directory again',async()=>{
 const h=saveDialogHarness();h.$('save-read').onclick();await h.$('game-save-folder').onclick();h.$('game-save-selection').value='1';
 await h.$('game-save-apply').onclick();assert.deepEqual([...h.context.saveProgress.solved],['a']);
 h.$('game-save-close').onclick();h.setBytes(statusFixture(33,[['a',1],['b',1]]));h.$('save-read').onclick();
 assert.equal(h.$('game-save-selection').value,'1');assert.equal(h.$('game-save-apply').disabled,false);assert.match(h.$('game-save-status').textContent,/已保留/);
 await h.$('game-save-apply').onclick();assert.deepEqual([...h.context.saveProgress.solved],['a','b']);assert.match(h.context.saveProgress.source,/two/);assert.equal(h.pickerCalls,1);assert.equal(h.fileReads,2);
 h.$('save-unbind').onclick();assert.equal(h.context.saveProgress,null);assert.equal(h.$('game-save-apply').disabled,true);
});

test('renewal only asks for read permission; denial, deleted or corrupt saves preserve existing progress',async()=>{
 const h=saveDialogHarness();h.$('save-read').onclick();await h.$('game-save-folder').onclick();await h.$('game-save-apply').onclick();
 h.setPermission('prompt');await h.$('game-save-apply').onclick();assert.equal(h.requests,1);
 const before=h.context.saveProgress;
 h.setPermission('denied');await h.$('game-save-apply').onclick();assert.equal(h.context.saveProgress,before);assert.match(h.$('game-save-status').textContent,/只读权限/);assert.equal(h.requests,1);
 h.setPermission('granted');h.setBytes(Buffer.from([33,0,0,0]));await h.$('game-save-apply').onclick();assert.equal(h.context.saveProgress,before);assert.match(h.$('game-save-status').textContent,/原来的标记保持不变/);
 h.setMissing();await h.$('game-save-apply').onclick();assert.equal(h.context.saveProgress,before);assert.match(h.$('game-save-status').textContent,/移动或删除/);
 runInContext('forgetGameSaveSelection()',h.context);assert.equal(h.$('game-save-apply').disabled,true);
});

test('one-shot directory fallback requires reselection instead of presenting stale File contents as new progress',async()=>{
 const h=saveDialogHarness({fallback:true});h.$('save-read').onclick();await h.$('game-save-folder').onclick();assert.equal(h.$('game-save-directory-input').clicked,true);
 h.$('game-save-directory-input').onchange({target:{files:[h.file()],value:'selected'}});await h.$('game-save-apply').onclick();
 assert.deepEqual([...h.context.saveProgress.solved],['a']);assert.equal(h.$('game-save-apply').disabled,true);assert.match(h.$('game-save-status').textContent,/重新选择目录/);
 h.$('game-save-close').onclick();h.$('save-read').onclick();assert.equal(h.$('game-save-apply').disabled,true);
});

// Opt-in local fixture generation for browser QA. Never publishes or reads a player's save.
if(process.env.OOTSS_SAVE_QA_FIXTURE==='1'){
 mkdirSync('cache/save-reader-qa',{recursive:true});
 writeFileSync('cache/save-reader-qa/Status.sokoban_status',statusFixture(33,[['end1',1],['heroes1_1',1],['heroes1_2_v2',2]]));
 writeFileSync('cache/save-reader-qa/invalid.sokoban_status',Buffer.from([33,0,0,0]));
}

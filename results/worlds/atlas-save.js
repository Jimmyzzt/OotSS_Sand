'use strict';
// Status format/version gates adapted from xPaw/order-of-the-sinking-cost (MIT).
// Revision e3d08b8411ebaaca3094c26cdb1c7bbcbf7c0be0; see assets/XPaw-LICENSE.txt.
globalThis.AtlasSave = {
  maxBytes: 8 * 1024 * 1024,
  parse(buffer){
    const bytes=buffer instanceof Uint8Array?buffer:new Uint8Array(buffer);
    if(bytes.byteLength>AtlasSave.maxBytes)throw Error('存档过大，请选择 Status.sokoban_status');
    const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),utf8=new TextDecoder('utf-8',{fatal:true});let offset=0;
    function skip(count){if(!Number.isSafeInteger(count)||count<0||offset+count>bytes.length)throw Error('存档不完整或格式不正确');offset+=count}
    function u32(){const start=offset;skip(4);return view.getUint32(start,true)}
    function u16(){const start=offset;skip(2);return view.getUint16(start,true)}
    function u8(){const start=offset;skip(1);return view.getUint8(start)}
    function string(){const length=u16(),start=offset;skip(length);return utf8.decode(bytes.subarray(start,offset))}
    const version=u32();if(version<5||version>33)throw Error(`不支持的存档版本 ${version}（支持 5–33）`);
    if(version>=30)skip(4);
    if(version>=12)skip(16);
    if(version>=19){skip(17);if(version>=22)skip(8);if(version>=27)skip(4)}
    skip(8);if(version<=25)skip(4);skip(version>=8?32:24);
    if(version>=13)skip(8);
    if(version>=9)skip(4);
    if(version>=11)skip(4);
    if(version>=19)skip(4);
    if(version>=20)skip(4);
    if(version>=16)skip(1);
    if(version>=24)skip(1);
    if(version>=23&&version<=31)skip(33);
    if(version>=17&&version<=20)skip(version===17?8:9);
    if(version<=24)string();
    string();if(version>=33)string();
    const count=u32();if(count>50000||count>Math.floor((bytes.length-offset)/3))throw Error('存档关卡列表不完整或过大');
    const solved=new Set();
    for(let i=0;i<count;i++){const name=string(),flags=u8();if((flags&1)!==0)solved.add(name)}
    // Later fields, history, fog and reachability are intentionally not read.
    return {version,solved:[...solved]};
  },
  statusFiles(files){return [...files].filter(file=>/^Status\.sokoban_status$/i.test(file.name)).sort((a,b)=>(a.webkitRelativePath||a.name).localeCompare(b.webkitRelativePath||b.name));},
  async findStatuses(directory){
    const found=[];let entries=0;
    async function scan(handle,path,depth){
      if(depth>5)return;
      for await(const [name,item]of handle.entries()){
        if(++entries>20000)throw Error('目录内容过多，请直接选择游戏档案目录或 Status.sokoban_status');
        if(item.kind==='directory')await scan(item,path+'/'+name,depth+1);
        else if(/^Status\.sokoban_status$/i.test(name))found.push({handle:item,path:path+'/'+name});
      }
    }
    await scan(directory,directory.name,0);return found.sort((a,b)=>a.path.localeCompare(b.path));
  }
};

function syncGameSaveButtons(){
  $('save-unbind').hidden=!saveProgress;
  $('save-read').title=saveProgress?`已读取：${saveProgress.source}；点击可重新读取`:'在本机读取通关状态，不上传存档';
}

function initGameSaves(){
  const dialog=$('game-save-dialog'),status=$('game-save-status'),selection=$('game-save-selection');let candidates=[],busy=false,generation=0;
  const allIds=new Set(worlds.flatMap(m=>m.levels.map(l=>l.level_id)));
  function message(text){status.textContent=text}
  function clearCandidates(){candidates=[];selection.replaceChildren();$('game-save-choice').hidden=true;$('game-save-apply').disabled=true}
  function busyState(value){busy=value;for(const id of ['game-save-folder','game-save-file','game-save-apply','game-save-selection'])$(id).disabled=value||id==='game-save-apply'&&!candidates.length}
  function showCandidates(list){
    clearCandidates();candidates=list;
    for(let i=0;i<list.length;i++){const option=document.createElement('option');option.value=i;option.textContent=list[i].path;selection.append(option)}
    $('game-save-choice').hidden=!list.length;$('game-save-apply').disabled=!list.length;
    message(list.length?'已找到存档。请选择一个游戏档案，再点击「读取并标记」。':'未找到 Status.sokoban_status，请选择游戏存档目录或该文件。');
  }
  function open(){
    settings(false);clearCandidates();message(saveProgress?`当前记录：${saveProgress.source}。再次读取会以存档通关结果重新覆盖显示。`:'请选择游戏存档目录，或直接选择 Status.sokoban_status。');dialog.showModal();
  }
  $('save-read').onclick=open;
  $('game-save-close').onclick=()=>{if(!busy)dialog.close()};dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault()});dialog.addEventListener('close',()=>{generation++;clearCandidates()});
  $('game-save-copy').onclick=async()=>{try{await navigator.clipboard.writeText($('game-save-path').textContent);message('已复制默认存档路径，可粘贴到系统文件选择窗口。')}catch{message('请选中上方路径后复制。')}};
  $('game-save-file').onclick=()=>$('game-save-file-input').click();
  $('game-save-file-input').onchange=event=>{showCandidates(AtlasSave.statusFiles(event.target.files).map(file=>({file,path:file.name})));event.target.value=''};
  $('game-save-directory-input').onchange=event=>{showCandidates(AtlasSave.statusFiles(event.target.files).map(file=>({file,path:file.webkitRelativePath||file.name})));event.target.value=''};
  $('game-save-folder').onclick=async()=>{
    if(!window.showDirectoryPicker){$('game-save-directory-input').click();return}
    const current=++generation;
    try{
      const directory=await window.showDirectoryPicker({id:'ootss-game-save',mode:'read'});if(current!==generation||!dialog.open)return;
      busyState(true);message('正在查找 Status.sokoban_status…');const found=await AtlasSave.findStatuses(directory);
      if(current===generation&&dialog.open)showCandidates(found);
    }catch(error){if(error.name!=='AbortError')message('无法读取此目录，请重选目录或直接选择存档文件。')}
    finally{busyState(false)}
  };
  $('game-save-apply').onclick=async()=>{
    if(busy)return;const candidate=candidates[Number(selection.value)];if(!candidate)return;const current=++generation;
    busyState(true);message('正在读取通关记录…');
    try{
      const file=candidate.file||await candidate.handle.getFile();if(file.size>AtlasSave.maxBytes)throw Error('存档过大，请检查选择的文件');
      const parsed=AtlasSave.parse(await file.arrayBuffer());if(current!==generation||!dialog.open)return;
      const solved=parsed.solved.filter(id=>allIds.has(id));
      remember();saveProgress=AtlasUI.newSaveProgress(solved,candidate.path,new Date().toISOString());saveEditorial();map.closePopup();applyPrefs();render();
      message(`读取成功：已标记地图中 ${solved.length} 个已完成关卡。另有 ${parsed.solved.length-solved.length} 个通关 ID 不在本地图，已忽略。`);
    }catch(error){message('读取失败：'+(error.message||'无法解析存档')+'。原来的标记保持不变。')}
    finally{busyState(false)}
  };
  $('save-unbind').onclick=()=>{if(busy)return;remember();saveProgress=null;saveEditorial();map.closePopup();applyPrefs();render()};
  syncGameSaveButtons();
}

'use strict';
// Feedback is loaded only when requested; local editorial data never leaves the browser.
function initFeedback(){
 const api='https://sand.zzt.si/api/feedback',dialog=$('feedback-dialog'),form=$('feedback-form'),message=$('feedback-status'),send=$('feedback-submit');
 let epoch=0;let context={},visits=[],token='',widget=null,loader=null,key=crypto.randomUUID(),busy=false,contextKey='';
 const notice=text=>{message.textContent=text};
 function selectedContext(){const v=visits[Number($('feedback-visit').value)];return {...context,...(v?{source_part:v.part,display_part:(DATA.parts||data.parts).find(p=>p.part===v.part)?.display_part??v.part,ordinal:v.ordinal,start:v.start,bvid:new URL(v.url).pathname.split('/').filter(Boolean).at(-1)}:{})}}
 async function verification(){
  const current=++epoch;send.disabled=true;notice('正在加载验证…');
  try{
   const response=await fetch(api+'/config');if(!response.ok)throw Error('反馈服务暂不可用，请稍后重试');const config=await response.json();if(!config.enabled)throw Error('反馈服务正在配置，请稍后重试');
   if(!window.turnstile){if(!loader)loader=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';script.async=true;script.onload=resolve;script.onerror=()=>{script.remove();loader=null;reject(Error('验证组件未加载，请检查网络后重试'))};document.head.append(script)});await loader}
   if(!dialog.open||current!==epoch)return;
   if(widget!==null)window.turnstile.remove(widget);
   token='';widget=window.turnstile.render($('feedback-verification'),{sitekey:config.sitekey,action:'feedback',theme:prefs.theme,size:$('feedback-verification').clientWidth<300?'compact':'normal',callback:value=>{token=value;send.disabled=busy;notice('')},'expired-callback':()=>{token='';send.disabled=true;notice('验证已过期，请重新验证')},'error-callback':()=>{token='';send.disabled=true;notice('验证未通过，请点击重新加载验证')}});
   notice('请完成验证后提交。');
  }catch(e){notice(e.message)}
 }
 function open(levelId,entryIndex=0){
  if(busy)return;
  const l=levelId?byId.get(levelId):null,nextKey=data.map_id+':'+(levelId||'global')+':'+entryIndex+':'+state.part;
  const previousVisit=nextKey===contextKey?$('feedback-visit').value:'0';
  if(nextKey!==contextKey){form.reset();key=crypto.randomUUID();contextKey=nextKey}
  context={map_id:data.map_id,map_commit:data.map_commit||'',tileset_revision:data.tileset_revision||''};
  if(state.part)Object.assign(context,{source_part:state.part,display_part:(DATA.parts||data.parts).find(p=>p.part===state.part)?.display_part??state.part,bvid:data.bvid});
  visits=l?l.visits.filter(v=>!state.part||v.part===state.part):[];
  if(l)Object.assign(context,{level_id:l.level_id,region_name:l.region_titles.join(' / '),marker_id:l.entries[entryIndex]?.marker_id,coordinates:l.entries[entryIndex]?.coordinates});
  // Only include published fields that actually exist in this atlas format.
  for(const k of Object.keys(context))if(context[k]===undefined)delete context[k];
  $('feedback-context').textContent=l?`${data.map_name} · ${l.level_id}`:`${data.map_name} · 全局问题 / 缺失关卡`;
  const select=$('feedback-visit');select.replaceChildren();visits.forEach((v,i)=>{const option=document.createElement('option');option.value=i;option.textContent=`${partName(v.part)} · 第 ${v.ordinal} 关 · ${clock(v.start)}`;select.append(option)});select.value=visits[Number(previousVisit)]?previousVisit:'0';$('feedback-visit-row').hidden=visits.length<2;
  dialog.showModal();verification();
 }
 $('feedback-open').onclick=()=>open();
 document.addEventListener('click',event=>{const trigger=event.target.closest('[data-feedback-level]');if(trigger){event.preventDefault();open(trigger.dataset.feedbackLevel,Number(trigger.dataset.feedbackEntry)||0)}});
 $('feedback-close').onclick=()=>{if(!busy)dialog.close()};
 dialog.addEventListener('cancel',e=>{if(busy)e.preventDefault()});
 dialog.addEventListener('close',()=>{epoch++;if(widget!==null&&window.turnstile){window.turnstile.remove(widget);widget=null}token='';send.disabled=true});
 $('feedback-retry').onclick=()=>{if(!busy)verification()};
 form.addEventListener('input',()=>{key=crypto.randomUUID()});
 form.addEventListener('change',()=>{key=crypto.randomUUID()});
 form.onsubmit=async event=>{
  event.preventDefault();if(busy||!token||!form.reportValidity())return;busy=true;send.disabled=true;$('feedback-close').disabled=true;$('feedback-retry').disabled=true;notice('正在提交…');
  const body={request_key:key,type:$('feedback-type').value,description:$('feedback-description').value,evidence_url:$('feedback-evidence').value,website:$('feedback-website').value,context:selectedContext(),turnstile_token:token};
  try{const response=await fetch(api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const result=await response.json();if(!response.ok)throw Error(result.error||'提交失败，请稍后重试');notice('已收到反馈，编号：'+result.id);form.reset();key=crypto.randomUUID();contextKey='';token='';if(widget!==null){window.turnstile.remove(widget);widget=null}}catch(e){notice(e.message||'网络异常，填写内容已保留');token='';if(widget!==null){window.turnstile.remove(widget);widget=null}}finally{busy=false;send.disabled=!token;$('feedback-close').disabled=false;$('feedback-retry').disabled=false}
 };
}

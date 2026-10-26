import {verifyAdmin} from './feedback-auth.js';
import {adminHtml} from './feedback-admin.js';

const TYPES=new Set(['mismatch','duplicate','missing','other']);
const STATUSES=new Set(['pending','confirmed','fixed','duplicate','invalid']);
const MAPS=new Set(['overworld','sky','underworld']);
const ORIGINS=new Set(['https://sand.zzt.si','https://jimmyzzt.github.io']);
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;
const BASE_HEADERS={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin'};
const json=(data,status=200,extra={})=>Response.json(data,{status,headers:{...BASE_HEADERS,...extra}});
const fail=(message,status=400)=>json({error:message},status);
const hex=bytes=>Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join('');
export const digest=async text=>hex(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)));

export async function limitedJson(request,max=16384){
  if(!request.headers.get('Content-Type')?.toLowerCase().startsWith('application/json'))throw Error('请使用 JSON 提交');
  if(Number(request.headers.get('Content-Length'))>max)throw Error('提交内容过大');
  if(!request.body)throw Error('提交内容为空');
  const reader=request.body.getReader(),chunks=[];let length=0;
  try{for(;;){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>max){await reader.cancel();throw Error('提交内容过大')}chunks.push(value)}}finally{reader.releaseLock()}
  const bytes=new Uint8Array(length);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length}
  return JSON.parse(new TextDecoder().decode(bytes));
}

export function validateFeedback(body){
  if(!body||typeof body!=='object'||!UUID.test(body.request_key||'')||!TYPES.has(body.type))throw Error('请选择反馈类型');
  if(body.website)throw Error('提交无效');
  const description=typeof body.description==='string'?body.description.trim():'';
  if(description.length<3||description.length>3000)throw Error('请填写 3–3000 字的问题描述');
  const raw=body.context;
  if(!raw||typeof raw!=='object'||!MAPS.has(raw.map_id))throw Error('地图信息无效');
  const context={map_id:raw.map_id};
  for(const [key,max]of [['level_id',100],['region_name',100],['map_commit',40],['tileset_revision',40]]){
    if(raw[key]!==undefined&&raw[key]!==null){if(typeof raw[key]!=='string'||raw[key].length>max)throw Error('关卡信息无效');context[key]=raw[key]}
  }
  if(context.level_id&&!/^[\w.-]+$/.test(context.level_id))throw Error('关卡编号无效');
  for(const [key,max]of [['source_part',1000],['display_part',1000],['ordinal',1000],['start',86400],['marker_id',Number.MAX_SAFE_INTEGER]]){
    if(raw[key]!==undefined&&raw[key]!==null){if(!Number.isFinite(raw[key])||raw[key]<0||raw[key]>max)throw Error('视频信息无效');context[key]=raw[key]}
  }
  if(raw.coordinates!==undefined){if(!Array.isArray(raw.coordinates)||raw.coordinates.length!==3||raw.coordinates.some(n=>!Number.isFinite(n)||Math.abs(n)>1000))throw Error('入口坐标无效');context.coordinates=[...raw.coordinates]}
  if(raw.bvid!==undefined){if(typeof raw.bvid!=='string'||!/^BV[0-9A-Za-z]{10}$/.test(raw.bvid))throw Error('视频编号无效');context.bvid=raw.bvid}
  if(context.bvid&&context.display_part)context.video_url=`https://www.bilibili.com/video/${context.bvid}/?p=${context.display_part}&t=${Math.floor(context.start||0)}`;
  let evidence_url=typeof body.evidence_url==='string'?body.evidence_url.trim():'';
  if(evidence_url){if(evidence_url.length>1000)throw Error('证据链接过长');const url=new URL(evidence_url);if(!['https:','http:'].includes(url.protocol)||url.username||url.password)throw Error('证据链接仅支持普通网页');evidence_url=url.href}
  return {request_key:body.request_key,type:body.type,description,evidence_url,context};
}

export async function validateTurnstile(token,env,origin,fetcher=fetch){
  if(typeof token!=='string'||!token||token.length>2048||!env.TURNSTILE_SECRET)return false;
  try{
    const response=await fetcher('https://challenges.cloudflare.com/turnstile/v0/siteverify',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({secret:env.TURNSTILE_SECRET,response:token}),signal:AbortSignal.timeout(10000)});
    if(!response.ok)return false;
    const value=await response.json();
    return value.success===true&&value.action==='feedback'&&value.hostname===new URL(origin).hostname;
  }catch{return false}
}

async function submit(request,env,ctx){
  if(!env.FEEDBACK_DB||!env.TURNSTILE_SECRET||!env.FEEDBACK_RATE_SALT)return fail('反馈服务正在配置，请稍后重试',503);
  let raw,value;try{raw=await limitedJson(request);value=validateFeedback(raw)}catch(e){return fail(e instanceof SyntaxError?'提交格式无效':e.message)}
  const canonical=JSON.stringify({type:value.type,description:value.description,evidence_url:value.evidence_url,context:value.context}),hash=await digest(canonical),db=env.FEEDBACK_DB;
  const existing=await db.prepare('SELECT id,payload_hash FROM feedback WHERE request_key=?').bind(value.request_key).first();
  if(existing)return existing.payload_hash===hash?json({id:existing.id,replayed:true},200):fail('此提交编号已用于其他内容，请重新打开反馈窗口',409);
  if(!await validateTurnstile(raw.turnstile_token,env,request.headers.get('Origin')))return fail('人机验证未通过或已过期，请重试',403);
  const ip=request.headers.get('CF-Connecting-IP');if(!ip)return fail('无法验证请求来源',403);
  const now=Date.now(),bucket=Math.floor(now/900000),key=await digest(env.FEEDBACK_RATE_SALT+'\0'+bucket+'\0'+ip);
  const rate=await db.prepare('INSERT INTO feedback_rate(key,expires_at,hits) VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET hits=hits+1 RETURNING hits').bind(key,Math.floor(now/1000)+86400).first();
  if(rate.hits>5)return json({error:'提交较频繁，请 15 分钟后再试'},429,{'Retry-After':'900'});
  const id=crypto.randomUUID(),created=new Date(now).toISOString();
  await db.prepare("INSERT INTO feedback(id,request_key,payload_hash,created_at,updated_at,type,map_id,level_id,description,evidence_url,context_json) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(request_key) DO NOTHING").bind(id,value.request_key,hash,created,created,value.type,value.context.map_id,value.context.level_id||null,value.description,value.evidence_url,JSON.stringify(value.context)).run();
  const stored=await db.prepare('SELECT id,payload_hash FROM feedback WHERE request_key=?').bind(value.request_key).first();
  if(stored.payload_hash!==hash)return fail('此提交编号已用于其他内容',409);
  const cleanup=db.prepare('DELETE FROM feedback_rate WHERE expires_at<?').bind(Math.floor(now/1000)).run().catch(()=>{});
  if(ctx?.waitUntil)ctx.waitUntil(cleanup);else await cleanup;
  return json({id:stored.id},201);
}

export function reportQuery(params,{exporting=false}={}){
  const filters=[],values=[];
  for(const [key,column,allowed]of [['status','status',STATUSES],['type','type',TYPES],['map','map_id',MAPS]]){
    const v=params.get(key);if(v){if(!allowed.has(v))throw Error('筛选值无效');filters.push(column+'=?');values.push(v)}
  }
  const q=(params.get('q')||'').trim();if(q.length>100)throw Error('搜索文字过长');
  if(q){filters.push("(level_id LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')");const text='%'+q.replace(/[\\%_]/g,'\\$&')+'%';values.push(text,text)}
  const cursor=params.get('cursor');if(cursor&&!exporting){
    let pair;try{pair=JSON.parse(atob(cursor))}catch{throw Error('分页参数无效')}
    if(!Array.isArray(pair)||pair.length!==2||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(pair[0])||!UUID.test(pair[1]))throw Error('分页参数无效');
    filters.push('(created_at<? OR (created_at=? AND id<?))');values.push(pair[0],pair[0],pair[1]);
  }
  return {where:filters.length?' WHERE '+filters.join(' AND '):'',values,limit:exporting?1000:51};
}

export function csvCell(value){let text=String(value??'');if(/^[\s]*[=+\-@]/.test(text)||/^[\t\r\n]/.test(text))text="'"+text;return '"'+text.replaceAll('"','""')+'"'}

async function admin(request,env,path){
  const identity=await verifyAdmin(request,env);if(!identity)return fail('仅限已通过 Cloudflare Access 认证的管理员',403);
  if(!env.FEEDBACK_DB)return fail('反馈数据库尚未配置',503);
  const db=env.FEEDBACK_DB,url=new URL(request.url);
  if((path==='/feedback-admin'||path==='/feedback-admin/')&&request.method==='GET'){
    const nonce=crypto.randomUUID();return new Response(adminHtml.replaceAll('__NONCE__',nonce),{headers:{...BASE_HEADERS,'Content-Type':'text/html; charset=utf-8','Content-Security-Policy':`default-src 'none'; script-src 'nonce-${nonce}'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'`,'X-Frame-Options':'DENY'}});
  }
  if(path==='/feedback-admin/api/me'&&request.method==='GET')return json(identity);
  if(path==='/feedback-admin/api/counts'&&request.method==='GET')return json((await db.prepare('SELECT status,COUNT(*) AS count FROM feedback GROUP BY status').all()).results);
  if(['/feedback-admin/api/reports','/feedback-admin/api/export.csv'].includes(path)&&request.method==='GET'){
    const exporting=path.endsWith('.csv');let query;try{query=reportQuery(url.searchParams,{exporting})}catch(e){return fail(e.message)}
    const rows=(await db.prepare('SELECT * FROM feedback'+query.where+' ORDER BY created_at DESC,id DESC LIMIT ?').bind(...query.values,query.limit).all()).results;
    if(exporting){const fields=['id','created_at','type','map_id','level_id','description','evidence_url','context_json','status','admin_note','updated_by'];return new Response('\ufeff'+[fields.join(','),...rows.map(r=>fields.map(k=>csvCell(r[k])).join(','))].join('\r\n'),{headers:{...BASE_HEADERS,'Content-Type':'text/csv; charset=utf-8','Content-Disposition':'attachment; filename="feedback.csv"'}})}
    const hasMore=rows.length>50;if(hasMore)rows.pop();const last=rows.at(-1);
    return json({items:rows,next:hasMore?btoa(JSON.stringify([last.created_at,last.id])):null});
  }
  const match=path.match(/^\/feedback-admin\/api\/reports\/([a-f0-9-]+)$/i);
  if(match&&UUID.test(match[1])&&request.method==='PATCH'){
    if(request.headers.get('Origin')!=='https://sand.zzt.si')return fail('请求来源无效',403);
    let body;try{body=await limitedJson(request,8192)}catch{return fail('修改内容无效')}
    if(!STATUSES.has(body.status)||typeof body.admin_note!=='string'||body.admin_note.length>2000||typeof body.updated_at!=='string')return fail('修改内容无效');
    const updated=new Date().toISOString(),result=await db.prepare('UPDATE feedback SET status=?,admin_note=?,updated_at=?,updated_by=? WHERE id=? AND updated_at=?').bind(body.status,body.admin_note,updated,identity.email,match[1],body.updated_at).run();
    return result.meta.changes?json({updated_at:updated}):fail('记录已被更新，请刷新后再修改',409);
  }
  return fail('不存在的管理接口',404);
}

export async function feedbackRoutes(request,env,ctx){
  const {pathname:path}=new URL(request.url);
  if(path==='/feedback-admin'||path.startsWith('/feedback-admin/')){
    try{return await admin(request,env,path)}catch{console.error(JSON.stringify({event:'feedback_admin_failed'}));return fail('读取反馈失败，请稍后重试',503)}
  }
  if(!['/api/feedback','/api/feedback/config'].includes(path))return null;
  const origin=request.headers.get('Origin'),allowed=ORIGINS.has(origin),cors=allowed?{'Access-Control-Allow-Origin':origin,'Vary':'Origin'}:{};
  if(request.method==='OPTIONS')return allowed?new Response(null,{status:204,headers:{...BASE_HEADERS,...cors,'Access-Control-Allow-Methods':'GET,POST,OPTIONS','Access-Control-Allow-Headers':'Content-Type'}}):fail('请求来源无效',403);
  let response;
  if(path.endsWith('/config')&&request.method==='GET')response=json({enabled:Boolean(env.FEEDBACK_DB&&env.TURNSTILE_SITEKEY&&env.TURNSTILE_SECRET&&env.FEEDBACK_RATE_SALT),sitekey:env.TURNSTILE_SITEKEY||''});
  else if(path==='/api/feedback'&&request.method==='POST'){
    if(!allowed)return fail('请求来源无效',403);
    try{response=await submit(request,env,ctx)}catch{console.error(JSON.stringify({event:'feedback_submit_failed'}));response=fail('提交暂时失败，已保留填写内容，请稍后重试',503)}
  }else response=fail('此接口不支持该方法',405);
  const headers=new Headers(response.headers);for(const [k,v]of Object.entries(cors))headers.set(k,v);
  return new Response(response.body,{status:response.status,headers});
}

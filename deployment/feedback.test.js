import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {generateKeyPair,exportJWK,SignJWT,createLocalJWKSet} from 'jose';
import {verifyAdmin} from './feedback-auth.js';
import {feedbackRoutes,limitedJson,validateFeedback,validateTurnstile,reportQuery,csvCell} from './feedback.js';
import {adminHtml} from './feedback-admin.js';

const origin='https://sand.zzt.si',domain='test-feedback.cloudflareaccess.com',aud='feedback-test-aud';
const {privateKey,publicKey}=await generateKeyPair('RS256'),jwk={...await exportJWK(publicKey),kid:'unit-test',alg:'RS256',use:'sig'},jwks={keys:[jwk]};
const localKeys=createLocalJWKSet(jwks),authEnv={ACCESS_TEAM_DOMAIN:domain,ACCESS_AUD:aud};
async function token(email='mocking.jimmy@gmail.com',extra={}){return new SignJWT({email,...extra.payload}).setProtectedHeader({alg:'RS256',kid:'unit-test'}).setIssuer(extra.issuer||'https://'+domain).setAudience(extra.audience||aud).setIssuedAt().setExpirationTime(extra.expiration||'1h').sign(extra.key||privateKey)}
function request(path,body,headers={}){return new Request(origin+path,{method:body===undefined?'GET':'POST',headers:{Origin:origin,'Content-Type':'application/json','CF-Connecting-IP':'192.0.2.1',...headers},body:body===undefined?undefined:JSON.stringify(body)})}
const body=()=>({request_key:crypto.randomUUID(),type:'mismatch',description:'测试：人物角色不一致',context:{map_id:'sky',level_id:'druid_3d_beam',source_part:26,display_part:27,ordinal:17,start:100,bvid:'BV13FH96bE4m',coordinates:[54,110,36]},turnstile_token:'test-token'});
function database(){
 const sql=new DatabaseSync(':memory:');
 sql.exec(readFileSync(new URL('./migrations/0001_feedback.sql',import.meta.url),'utf8'));
 sql.exec(readFileSync(new URL('./migrations/0002_intro_map.sql',import.meta.url),'utf8'));
 return {sql,prepare(text){return {bind(...values){const s=sql.prepare(text);return {
  async first(){return s.get(...values)||null},
  async all(){return {results:s.all(...values)}},
  async run(){return {meta:{changes:Number(s.run(...values).changes)}}}
 }}}}};
}
async function mockFetch(fn,run){const previous=globalThis.fetch;globalThis.fetch=fn;try{return await run()}finally{globalThis.fetch=previous}}
const verified=()=>Response.json({success:true,hostname:'sand.zzt.si',action:'feedback'});

test('intro migration preserves complete reports and permits the fourth map',()=>{
 const sql=new DatabaseSync(':memory:');sql.exec(readFileSync(new URL('./migrations/0001_feedback.sql',import.meta.url),'utf8'));
 sql.exec("INSERT INTO feedback(id,request_key,payload_hash,created_at,updated_at,type,map_id,description,context_json,status,admin_note,updated_by) VALUES('old','request','hash','date','date','other','sky','player report','{}','confirmed','reviewed','owner')");
 const previous=sql.prepare('SELECT * FROM feedback').get();
 sql.exec(readFileSync(new URL('./migrations/0002_intro_map.sql',import.meta.url),'utf8'));
 assert.deepEqual(sql.prepare('SELECT * FROM feedback').get(),previous);
 sql.prepare('UPDATE feedback SET map_id=? WHERE id=?').run('intro','old');
 assert.equal(sql.prepare('SELECT map_id FROM feedback').get().map_id,'intro');
 assert.throws(()=>sql.prepare('UPDATE feedback SET map_id=?').run('invalid'));
 assert.equal(sql.prepare("SELECT count(*) AS n FROM sqlite_master WHERE type='index' AND name LIKE 'feedback_%'").get().n,4);
 assert.equal(validateFeedback({...body(),context:{map_id:'intro',level_id:'intro-heroes1_7_v2'}}).context.map_id,'intro');
 sql.close();
});

test('Access verifies signature, issuer, audience, expiry and the exact email allowlist',async()=>{
 for(const email of ['mocking.jimmy@gmail.com','2601848284@qq.com'])assert.deepEqual(await verifyAdmin(request('/feedback-admin',undefined,{'Cf-Access-Jwt-Assertion':await token(email)}),authEnv,localKeys),{email});
 for(const invalid of [await token('someone@example.com'),await token('mocking.jimmy@gamil.com'),await token(undefined,{issuer:'https://evil.test'}),await token(undefined,{audience:'another-app'}),await token(undefined,{expiration:1}),await token(undefined,{key:(await generateKeyPair('RS256')).privateKey}),'not.a.jwt'])assert.equal(await verifyAdmin(request('/feedback-admin',undefined,{'Cf-Access-Jwt-Assertion':invalid}),authEnv,localKeys),null);
 assert.equal(await verifyAdmin(request('/feedback-admin',undefined,{'Cf-Access-Authenticated-User-Email':'mocking.jimmy@gmail.com'}),authEnv,localKeys),null);
 assert.equal(await verifyAdmin(new Request('https://ootss-sand.workers.dev/feedback-admin',{headers:{'Cf-Access-Jwt-Assertion':await token()}}),authEnv,localKeys),null);
 assert.equal(await verifyAdmin(request('/feedback-admin',undefined,{'Cf-Access-Jwt-Assertion':await token()}),{},localKeys),null);
});

test('feedback validates bounded content, whitelists context and reconstructs video links',()=>{
 const raw=body();raw.context.local_notes='must not leave browser';raw.context.video_url='https://evil.test';const value=validateFeedback(raw);
 assert.equal(value.context.local_notes,undefined);assert.equal(value.context.video_url,'https://www.bilibili.com/video/BV13FH96bE4m/?p=27&t=100');
 for(const changes of [{description:'a'},{description:'a'.repeat(3001)},{type:'sql'},{website:'spam'},{request_key:'bad'},{evidence_url:'javascript:alert(1)'},{evidence_url:'https://user:password@example.com/'}])assert.throws(()=>validateFeedback({...body(),...changes}));
 for(const context of [{map_id:'bad'},{map_id:'sky',coordinates:[Infinity,1,2]},{map_id:'sky',level_id:'<script>'},{map_id:'sky',bvid:'invalid'}])assert.throws(()=>validateFeedback({...body(),context}));
});

test('streamed JSON has a real byte bound, not only a Content-Length check',async()=>{
 assert.deepEqual(await limitedJson(request('/api/feedback',{a:1}),7),{a:1});
 await assert.rejects(limitedJson(request('/api/feedback',{a:'中'.repeat(20)}),20),/过大/);
 await assert.rejects(limitedJson(new Request(origin,{method:'POST',body:'{}',headers:{'Content-Type':'text/plain'}})),/JSON/);
});

test('Turnstile requires success, action and the requesting hostname',async()=>{
 const env={TURNSTILE_SECRET:'unit-test-secret'};
 assert.equal(await validateTurnstile('t',env,origin,async()=>verified()),true);
 for(const result of [{success:false},{success:true,hostname:'evil.test',action:'feedback'},{success:true,hostname:'sand.zzt.si',action:'login'}])assert.equal(await validateTurnstile('t',env,origin,async()=>Response.json(result)),false);
 assert.equal(await validateTurnstile('',env,origin),false);
});

test('public submit persists once, retries idempotently, and limits verified abuse',async()=>{
 const db=database(),env={FEEDBACK_DB:db,TURNSTILE_SECRET:'unit-test',FEEDBACK_RATE_SALT:'unit-test-salt'};
 await mockFetch(verified,async()=>{
  const first=body(),r=await feedbackRoutes(request('/api/feedback',first),env),id=(await r.json()).id;assert.equal(r.status,201);
  const replay=await feedbackRoutes(request('/api/feedback',{...first,turnstile_token:''}),env);assert.equal(replay.status,200);assert.equal((await replay.json()).id,id);
  assert.equal((await feedbackRoutes(request('/api/feedback',{...first,description:'changed content'}),env)).status,409);
  for(let i=0;i<4;i++)assert.equal((await feedbackRoutes(request('/api/feedback',body()),env)).status,201);
  assert.equal((await feedbackRoutes(request('/api/feedback',body()),env)).status,429);
  assert.equal(db.sql.prepare('SELECT COUNT(*) n FROM feedback').get().n,5);
  const rate=db.sql.prepare('SELECT key FROM feedback_rate').get();assert.match(rate.key,/^[a-f0-9]{64}$/);assert.equal(db.sql.prepare('SELECT context_json FROM feedback LIMIT 1').get().context_json.includes('192.0.2.1'),false);
 });db.sql.close();
});

test('invalid verification or hostile origin cannot create a report; CORS is bounded',async()=>{
 const db=database(),env={FEEDBACK_DB:db,TURNSTILE_SITEKEY:'public-key',TURNSTILE_SECRET:'unit-test',FEEDBACK_RATE_SALT:'unit-test-salt'};
 await mockFetch(async()=>Response.json({success:false}),async()=>assert.equal((await feedbackRoutes(request('/api/feedback',body()),env)).status,403));
 assert.equal((await feedbackRoutes(request('/api/feedback',body(),{Origin:'https://evil.test'}),env)).status,403);
 assert.equal(db.sql.prepare('SELECT COUNT(*) n FROM feedback').get().n,0);
 const c=await feedbackRoutes(request('/api/feedback/config'),env);assert.equal(c.headers.get('Cache-Control'),'no-store');assert.equal(c.headers.get('Access-Control-Allow-Origin'),origin);assert.deepEqual(await c.json(),{enabled:true,sitekey:'public-key'});
 assert.equal((await feedbackRoutes(new Request(origin+'/api/feedback',{method:'OPTIONS',headers:{Origin:'https://evil.test'}}),env)).status,403);
 db.sql.close();
});

test('management page, list, CSV and updates all require a valid Access assertion',async()=>{
 const db=database();for(const path of ['/feedback-admin','/feedback-admin/','/feedback-admin/api/reports','/feedback-admin/api/export.csv']){
  const r=await feedbackRoutes(request(path),{FEEDBACK_DB:db,...authEnv});assert.equal(r.status,403);assert.equal(r.headers.get('Cache-Control'),'no-store');
 }db.sql.close();
});

test('authenticated management supports safe search, pagination, CSV and conflict checks',async()=>{
 const db=database(),env={FEEDBACK_DB:db,...authEnv},jwt=await token(),headers={'Cf-Access-Jwt-Assertion':jwt};
 const id=crypto.randomUUID(),stamp='2026-10-26T10:00:00.000Z';db.sql.prepare('INSERT INTO feedback(id,request_key,payload_hash,created_at,updated_at,type,map_id,level_id,description,context_json) VALUES(?,?,?,?,?,?,?,?,?,?)').run(id,crypto.randomUUID(),'hash',stamp,stamp,'mismatch','sky','level_1','=1+1 test%_{}','{}');
 await mockFetch(async url=>{assert.equal(String(url),'https://'+domain+'/cdn-cgi/access/certs');return Response.json(jwks)},async()=>{
  const page=await feedbackRoutes(request('/feedback-admin',undefined,headers),env);assert.equal(page.status,200);assert.match(page.headers.get('Content-Security-Policy'),/nonce-/);assert.equal((await page.text()).includes('__NONCE__'),false);
  const list=await feedbackRoutes(request('/feedback-admin/api/reports?q='+encodeURIComponent('%_'),undefined,headers),env);assert.equal((await list.json()).items.length,1);
  assert.equal((await (await feedbackRoutes(request('/feedback-admin/api/reports?q='+encodeURIComponent("' OR 1=1--"),undefined,headers),env)).json()).items.length,0);
  const csv=await feedbackRoutes(request('/feedback-admin/api/export.csv',undefined,headers),env);assert.match(await csv.text(),/"'=1\+1/);
  const patch=(updated_at,originHeader=origin)=>new Request(origin+'/feedback-admin/api/reports/'+id,{method:'PATCH',headers:{...headers,Origin:originHeader,'Content-Type':'application/json'},body:JSON.stringify({status:'fixed',admin_note:'checked',updated_at})});
  assert.equal((await feedbackRoutes(patch(stamp,'https://evil.test'),env)).status,403);assert.equal((await feedbackRoutes(patch(stamp),env)).status,200);assert.equal((await feedbackRoutes(patch(stamp),env)).status,409);
  assert.equal(db.sql.prepare('SELECT updated_by FROM feedback WHERE id=?').get(id).updated_by,'mocking.jimmy@gmail.com');
  for(let i=0;i<51;i++)db.sql.prepare('INSERT INTO feedback(id,request_key,payload_hash,created_at,updated_at,type,map_id,description,context_json) VALUES(?,?,?,?,?,?,?,?,?)').run(crypto.randomUUID(),crypto.randomUUID(),'h',stamp,stamp,'other','sky','page test','{}');
  const first=await (await feedbackRoutes(request('/feedback-admin/api/reports',undefined,headers),env)).json();assert.equal(first.items.length,50);assert.ok(first.next);
  const second=await (await feedbackRoutes(request('/feedback-admin/api/reports?cursor='+encodeURIComponent(first.next),undefined,headers),env)).json();assert.equal(second.items.length,2);assert.equal(second.next,null);assert.equal(new Set([...first.items,...second.items].map(r=>r.id)).size,52);
 });db.sql.close();
});

test('filters reject invalid cursors and CSV neutralizes spreadsheet formulas',()=>{
 for(const q of ['status=bad','cursor=invalid','q='+'x'.repeat(101)])assert.throws(()=>reportQuery(new URLSearchParams(q)));
 assert.equal(csvCell('@cmd'), '"\'@cmd"');assert.equal(csvCell('normal,"quoted"'),'"normal,""quoted"""');
});

test('embedded admin JavaScript parses and stored feedback uses text rendering',()=>{
 const script=adminHtml.match(/<script nonce="__NONCE__">([\s\S]*?)<\/script>/)[1];assert.doesNotThrow(()=>new vm.Script(script));assert.equal(script.includes('innerHTML'),false);
});

import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import worker from './worker.js';

test('public requests use the asset binding without any GitHub subrequest, preserving status and HEAD',async()=>{
 const previous=globalThis.fetch;globalThis.fetch=()=>{throw Error('public requests must not proxy upstream')};
 const calls=[],env={ASSETS:{async fetch(request){calls.push(request);return new Response(request.method==='HEAD'?null:'static bytes',{status:404,headers:{'Content-Type':'image/webp'}})}}};
 try{
  const response=await worker.fetch(new Request('https://sand.zzt.si/assets/a.webp'),env);
  assert.equal(response.status,404);assert.equal(await response.text(),'static bytes');assert.equal(response.headers.get('Content-Type'),'image/webp');
  assert.equal((await worker.fetch(new Request('https://sand.zzt.si/assets/a.webp',{method:'HEAD'}),env)).body,null);
  assert.equal((await worker.fetch(new Request('https://sand.zzt.si/',{method:'POST'}),env)).status,405);assert.equal(calls.length,2);
 }finally{globalThis.fetch=previous}
});

test('feedback and admin stay dynamic and never fall through to public assets',async()=>{
 const env={ASSETS:{fetch(){throw Error('private and API routes must not use public assets')}}};
 const config=await worker.fetch(new Request('https://sand.zzt.si/api/feedback/config'),env);assert.equal(config.status,200);assert.equal((await config.json()).enabled,false);
 assert.equal((await worker.fetch(new Request('https://sand.zzt.si/feedback-admin'),env)).status,403);
 assert.equal((await worker.fetch(new Request('https://sand.zzt.si/feedback-admin/api/reports'),env)).status,403);
});

test('routing explicitly bypasses script execution for public maps, tiles and the backup redirect',()=>{
 const config=JSON.parse(readFileSync('wrangler.jsonc','utf8')),rules=config.assets.run_worker_first;
 const matches=(pattern,path)=>new RegExp('^'+pattern.replace(/[.+?^${}()|[\]\\]/g,'\\$&').replaceAll('*','.*')+'$').test(path);
 for(const path of ['/','/index.html','/atlas.js','/assets/levels/a.webp','/tiles/sky_64k/7/2/3.webp','/audit.html','/backup','/map-tiles/revision/sky/6/1/2.svg'])assert.ok(rules.some(r=>r.startsWith('!')&&matches(r.slice(1),path)),path);
 for(const path of ['/api/feedback','/feedback-admin','/feedback-admin/api/reports']){assert.ok(rules.some(r=>!r.startsWith('!')&&matches(r,path)));assert.equal(rules.some(r=>r.startsWith('!')&&matches(r.slice(1),path)),false)}
 assert.equal(config.assets.html_handling,'auto-trailing-slash');assert.equal(config.assets.binding,'ASSETS');assert.equal(config.vars.PAGES_ORIGIN,undefined);
});

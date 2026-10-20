import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker,{upstreamUrl} from './worker.js';
const env={PAGES_ORIGIN:'https://jimmyzzt.github.io/OotSS_Sand/'};
test('fixed Pages prefix and queries survive; arbitrary hosts cannot be selected',()=>{
  assert.equal(upstreamUrl('https://sand.zzt.si/assets/a.webp?p=5',env.PAGES_ORIGIN).href,'https://jimmyzzt.github.io/OotSS_Sand/assets/a.webp?p=5');
  assert.equal(upstreamUrl('https://sand.zzt.si//evil.test/x',env.PAGES_ORIGIN).hostname,'jimmyzzt.github.io');
  assert.throws(()=>upstreamUrl('https://sand.zzt.si/%2e%2e%2fother',env.PAGES_ORIGIN));
});
test('proxy streams assets, drops cookies and authorization, preserves 404 and HEAD',async()=>{
  const original=globalThis.fetch;
  globalThis.fetch=async(url,options)=>{
    assert.equal(options.headers.has('cookie'),false);assert.equal(options.headers.has('authorization'),false);
    return new Response(options.method==='HEAD'?null:'image bytes',{status:404,headers:{'Content-Type':'image/webp'}});
  };
  try{
    const response=await worker.fetch(new Request('https://sand.zzt.si/a.webp',{headers:{cookie:'private',authorization:'Bearer private'}}),env);
    assert.equal(response.status,404);assert.equal(await response.text(),'image bytes');
    assert.equal(response.headers.get('Content-Type'),'image/webp');
    assert.equal((await worker.fetch(new Request('https://sand.zzt.si/a',{method:'HEAD'}),env)).body,null);
    assert.equal((await worker.fetch(new Request('https://sand.zzt.si/',{method:'POST'}),env)).status,405);
  }finally{globalThis.fetch=original}
});

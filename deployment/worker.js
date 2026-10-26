// Fixed-origin streaming proxy for the public GitHub Pages atlas.
import {feedbackRoutes} from './feedback.js';
export function upstreamUrl(requestUrl, origin) {
  const base=new URL(origin),input=new URL(requestUrl);
  const pinnedTiles=base.hostname==='raw.githubusercontent.com'&&/^\/joric\/ootss_tileset\/[a-f0-9]{40}\/$/.test(base.pathname);
  if(base.protocol!=='https:'||!base.hostname.endsWith('.github.io')&&!pinnedTiles)throw Error('Invalid configured origin');
  const path=decodeURIComponent(input.pathname);
  if(path.split('/').some(p=>p==='..'||p==='.')||path.includes('\\'))throw Error('Invalid path');
  const target=new URL(base.href);
  target.pathname=base.pathname.replace(/\/?$/,'/')+input.pathname.replace(/^\/+/, '');
  if(!target.pathname.startsWith(base.pathname))throw Error('Path escaped origin prefix');
  target.search=input.search;
  return target;
}

export default {
  async fetch(request,env,ctx) {
    const feedback=await feedbackRoutes(request,env,ctx);if(feedback)return feedback;
    if(!['GET','HEAD'].includes(request.method))return new Response('Method not allowed',{status:405,headers:{Allow:'GET, HEAD'}});
    const input=new URL(request.url),tile=/^\/tiles\/(?:overworld|sky|underworld)_64k\/[0-7]\/\d+\/\d+\.webp$/.test(input.pathname),revision=input.searchParams.get('v');
    if(tile&&revision&&!/^[a-f0-9]{40}$/.test(revision))return new Response('Invalid tileset revision',{status:400});
    const tileOrigin=revision?`https://raw.githubusercontent.com/joric/ootss_tileset/${revision}/`:'https://joric.github.io/ootss_tileset/';
    let target;try{target=upstreamUrl(request.url,tile?tileOrigin:env.PAGES_ORIGIN)}catch{return new Response('Invalid request path or origin',{status:400})}
    const headers=new Headers();
    for(const key of ['Accept','If-None-Match','If-Modified-Since','Range'])if(request.headers.has(key))headers.set(key,request.headers.get(key));
    let upstream;
    try{upstream=await fetch(target,{method:request.method,headers,redirect:'manual'})}catch{console.error(JSON.stringify({event:'pages_origin_unreachable'}));return new Response('地图源站暂时不可用，请稍后重试。',{status:502})}
    const responseHeaders=new Headers(upstream.headers);
    responseHeaders.set('X-Content-Type-Options','nosniff');
    responseHeaders.set('Referrer-Policy','strict-origin-when-cross-origin');
    responseHeaders.set('Cache-Control',target.pathname.endsWith('.webp')?'public, max-age=86400':'public, max-age=60');
    const location=responseHeaders.get('Location');
    if(location){const redirect=new URL(location,target);if(redirect.origin===target.origin&&redirect.pathname.startsWith(new URL(env.PAGES_ORIGIN).pathname)){const local=new URL(request.url);local.pathname=redirect.pathname.slice(new URL(env.PAGES_ORIGIN).pathname.length-1);local.search=redirect.search;responseHeaders.set('Location',local.href)}}
    return new Response(request.method==='HEAD'?null:upstream.body,{status:upstream.status,statusText:upstream.statusText,headers:responseHeaders});
  }
};

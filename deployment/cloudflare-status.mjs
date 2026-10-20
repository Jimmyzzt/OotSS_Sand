// Read-only account check. Credentials remain in memory and are never printed.
import { execFileSync } from 'node:child_process';
const output=execFileSync(process.execPath,['node_modules/wrangler/bin/wrangler.js','auth','token','--json'],{encoding:'utf8',env:{...process.env,WRANGLER_LOG_PATH:'cache/wrangler.log'}});
let auth;try{auth=JSON.parse(output)}catch{throw Error('Wrangler token response was not JSON')}
if(!auth.token)throw Error('Wrangler did not return a bearer token');
async function api(path){const r=await fetch('https://api.cloudflare.com/client/v4/'+path,{headers:{Authorization:'Bearer '+auth.token}});const d=await r.json();if(!d.success)throw Error('Cloudflare API check failed: HTTP '+r.status);return d.result}
const account='e8f2bb86459172e43e34fb3509041e02';
const zones=await api('zones?name=zzt.si');
const domains=await api(`accounts/${account}/workers/domains`);
console.log(JSON.stringify({zones:zones.map(z=>({id:z.id,name:z.name,status:z.status,account_id:z.account.id})),existing_sand_domain:domains.filter(d=>d.hostname==='sand.zzt.si')},null,2));

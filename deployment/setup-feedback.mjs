// Idempotent resource setup. Only public identifiers are printed or saved to Git.
import {execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync} from 'node:fs';
import {randomBytes} from 'node:crypto';

const apply=process.argv.includes('--apply');
const configPath='wrangler.jsonc',config=JSON.parse(readFileSync(configPath,'utf8'));
if(config.account_id!=='e8f2bb86459172e43e34fb3509041e02'||config.name!=='ootss-sand')throw Error('Unexpected deployment target');
const cliEnv={...process.env,WRANGLER_WRITE_LOGS:'false',WRANGLER_LOG_SANITIZE:'true',WRANGLER_SEND_METRICS:'false'};
function cli(args,input){try{return execFileSync(process.execPath,['node_modules/wrangler/bin/wrangler.js',...args],{encoding:'utf8',input,env:cliEnv,stdio:['pipe','pipe','pipe']})}catch{throw Error('Wrangler operation failed: '+args.slice(0,2).join(' '))}}
const auth=JSON.parse(cli(['auth','token','--json']));if(!auth.token)throw Error('Not logged in');
async function api(path,method='GET',body){
 const r=await fetch('https://api.cloudflare.com/client/v4/accounts/'+config.account_id+'/'+path,{method,headers:{Authorization:'Bearer '+auth.token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
 const data=await r.json();if(!data.success)throw Error('Cloudflare operation failed: '+method+' '+path+' HTTP '+r.status+' codes '+(data.errors||[]).map(e=>e.code).join(','));return data.result;
}
const dbs=await api('d1/database'),widgets=await api('challenges/widgets'),secretNames=new Set((await api('workers/scripts/ootss-sand/secrets')).map(s=>s.name));
let db=dbs.find(d=>d.name==='ootss-sand-feedback'),matches=widgets.filter(w=>w.name==='ootss-sand-feedback');
if(matches.length>1)throw Error('More than one feedback widget found');
let widget=matches[0];
if(!apply){console.log(JSON.stringify({database:db?.uuid||null,widget:widget?{sitekey:widget.sitekey,domains:widget.domains}:null,secrets_present:['TURNSTILE_SECRET','FEEDBACK_RATE_SALT'].filter(k=>secretNames.has(k))},null,2));process.exit(0)}
if(!db)db=await api('d1/database','POST',{name:'ootss-sand-feedback',primary_location_hint:'apac'});
if(!widget)widget=await api('challenges/widgets','POST',{name:'ootss-sand-feedback',domains:['sand.zzt.si','jimmyzzt.github.io'],mode:'managed',clearance_level:'no_clearance'});
if(widget.domains.length!==2||!['sand.zzt.si','jimmyzzt.github.io'].every(d=>widget.domains.includes(d)))throw Error('Unexpected Turnstile hostnames');
config.d1_databases=[...(config.d1_databases||[]).filter(d=>d.binding!=='FEEDBACK_DB'),{binding:'FEEDBACK_DB',database_name:db.name,database_id:db.uuid,migrations_dir:'deployment/migrations'}];
Object.assign(config.vars,{TURNSTILE_SITEKEY:widget.sitekey,ACCESS_TEAM_DOMAIN:config.vars.ACCESS_TEAM_DOMAIN||'',ACCESS_AUD:config.vars.ACCESS_AUD||''});
writeFileSync(configPath,JSON.stringify(config,null,2)+'\n');
if(!secretNames.has('TURNSTILE_SECRET')){
 if(!widget.secret)widget=await api('challenges/widgets/'+widget.sitekey);
 if(typeof widget.secret!=='string'||!widget.secret.trim())throw Error('Widget secret missing');
 cli(['secret','put','TURNSTILE_SECRET'],widget.secret);widget.secret=undefined;
}
if(!secretNames.has('FEEDBACK_RATE_SALT'))cli(['secret','put','FEEDBACK_RATE_SALT'],randomBytes(32).toString('hex'));
console.log(JSON.stringify({account:config.account_id,worker:config.name,database:db.uuid,sitekey:widget.sitekey,domains:widget.domains,secrets_configured:true},null,2));

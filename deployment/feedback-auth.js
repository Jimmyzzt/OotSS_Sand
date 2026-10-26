import {createRemoteJWKSet,jwtVerify} from 'jose';

const keySets=new Map();
export const ADMIN_EMAILS=new Set(['mocking.jimmy@gmail.com','2601848284@qq.com']);

export async function verifyAdmin(request,env,keys){
  const token=request.headers.get('Cf-Access-Jwt-Assertion');
  if(!token||token.length>16384||!env.ACCESS_TEAM_DOMAIN||!env.ACCESS_AUD)return null;
  const domain=env.ACCESS_TEAM_DOMAIN;
  if(!/^[a-z0-9-]+\.cloudflareaccess\.com$/.test(domain))return null;
  if(new URL(request.url).hostname!=='sand.zzt.si')return null;
  try{
    const issuer='https://'+domain;
    if(!keys){
      if(!keySets.has(domain))keySets.set(domain,createRemoteJWKSet(new URL(issuer+'/cdn-cgi/access/certs'),{timeoutDuration:5000}));
      keys=keySets.get(domain);
    }
    const {payload}=await jwtVerify(token,keys,{issuer,audience:env.ACCESS_AUD,algorithms:['RS256'],requiredClaims:['exp','iat','email']});
    const email=typeof payload.email==='string'?payload.email.toLowerCase():'';
    return ADMIN_EMAILS.has(email)?{email}:null;
  }catch{return null}
}

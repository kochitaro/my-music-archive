/* MusicBrainz search shared by MMA and Search Lab. Only traffic timing is shared. */
(()=>{'use strict';
const BASE='https://musicbrainz.org/ws/2/',CACHE_MS=300000,CACHE_LIMIT=180;
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const norm=s=>(s||'').normalize('NFKC').toLocaleLowerCase().replace(/[’‘]/g,"'").replace(/\s+/g,' ').trim();
const hira=s=>s.replace(/[ァ-ヶ]/g,c=>String.fromCharCode(c.charCodeAt(0)-0x60));
const kata=s=>s.replace(/[ぁ-ゖ]/g,c=>String.fromCharCode(c.charCodeAt(0)+0x60));
const searchNorm=s=>hira(norm(s)).replace(/\s+/g,'');
const escape=s=>s.replace(/[+\-!(){}\[\]^"~*?:\\/|&]/g,'\\$&');
const rank=r=>({Album:0,EP:1,Single:2})[r['primary-type']]??3;
const sort=(a,b)=>rank(a)-rank(b)||(b['first-release-date']||'').localeCompare(a['first-release-date']||'')||(a.title||'').localeCompare(b.title||'')||a.id.localeCompare(b.id);
// Title searches use the existing normalization, independently of artist type priority.
function sortTitles(items,q){
 const query=searchNorm(q),match=r=>{const title=searchNorm(r.title);return title===query?0:title.includes(query)?1:2};
 return [...items].sort((a,b)=>match(a)-match(b)||(b['first-release-date']||'').localeCompare(a['first-release-date']||'')||(a.title||'').localeCompare(b.title||'')||a.id.localeCompare(b.id));
}
const unique=items=>{const seen=new Set();return items.filter(r=>r?.id&&!seen.has(r.id)&&seen.add(r.id))};
function credit(r){return (r['artist-credit']||[]).map(a=>typeof a==='string'?a:(a.name||a.artist?.name||'')+(a.joinphrase||'')).join('').trim()}
function current(ctx){if(ctx?.isCurrent&&!ctx.isCurrent())throw new Error('Search superseded')}
function artistQuality(q,a){
  const n=searchNorm(q),names=[a.name,a['sort-name'],...(a.aliases||[]).flatMap(x=>[x.name,x['sort-name']])].filter(Boolean).map(searchNorm);
  if(names.some(v=>v===n))return 3;
  // Short prefixes still require a registered name match. Ambiguous matches are selected by the user.
  const ratios=n.length>=2?names.filter(v=>v.startsWith(n)).map(v=>n.length/v.length):[];
  return ratios.length?1+Math.max(...ratios):0;
}
function url(entity,params){return BASE+entity+'?'+new URLSearchParams({...params,fmt:'json'})}
// This state belongs only to MusicBrainz traffic; never use the archive save lock.
const TRAFFIC_KEY='mla:musicbrainz:traffic:v1',TRAFFIC_LOCK='mla:musicbrainz:request:v1';
const INTERVAL=1250,WAIT_LIMIT=30000,MAX_TIME=Number.MAX_SAFE_INTEGER;
const retryable=code=>[429,502,503,504].includes(code);
const searchError=(code,message)=>Object.assign(new Error(message),{searchCode:code});
let queue=Promise.resolve(),epoch=0,storageFailed=false,clockFailed=false;
let wall=Date.now(),mono=performance.now();
const activeControllers=new Set();
const interrupt=()=>{++epoch;for(const c of activeControllers)c.abort()};
document.addEventListener('visibilitychange',()=>{if(document.hidden)interrupt()});
window.addEventListener('pagehide',interrupt);
window.addEventListener('pageshow',e=>{if(e.persisted)interrupt()});
function now(){
 const w=Date.now(),m=performance.now();
 // A wall-clock jump must not shorten a live tab's shared cooldown.
 if(Math.abs((w-wall)-(m-mono))>250)clockFailed=true;
 wall=w;mono=m;
 if(clockFailed)throw searchError('clock','Device clock changed; search paused');
 return w;
}
let observedState=false;
function readTraffic(){
 if(storageFailed)throw searchError('storage','Search coordination storage unavailable');
 try{
  const raw=localStorage.getItem(TRAFFIC_KEY);
  if(raw===null){if(observedState)throw Error('Shared state removed');return {version:1,lastStartAt:0,cooldownUntil:0}}
  const s=JSON.parse(raw);
  if(!s||Object.keys(s).sort().join(',')!=='cooldownUntil,lastStartAt,version'||s.version!==1||
   !Number.isSafeInteger(s.lastStartAt)||s.lastStartAt<0||
   !(s.cooldownUntil===null||Number.isSafeInteger(s.cooldownUntil)&&s.cooldownUntil>=0))throw Error('Invalid shared state');
  observedState=true;return s;
 }catch(e){storageFailed=true;throw searchError('storage','Search coordination state unavailable')}
}
function writeTraffic(s){
 try{const raw=JSON.stringify(s);localStorage.setItem(TRAFFIC_KEY,raw);if(localStorage.getItem(TRAFFIC_KEY)!==raw)throw Error('Shared write not verified');observedState=true}
 catch(e){storageFailed=true;throw searchError('storage','Search coordination state could not be saved')}
}
// null means a valid server delay beyond safe representation: block, never cap it.
function retryDelay(header,at){
 if(!header)return 0;
 const h=header.trim();
 if(/^\d+(?:\.\d+)?$/.test(h)){
  const delay=Math.ceil(Number(h)*1000);return Number.isSafeInteger(delay)&&delay<=MAX_TIME-at?delay:null;
 }
 // Restrict Date.parse to the three HTTP-date grammars (not strings such as '10x').
 const day='(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)',month='(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)';
 const imf=new RegExp('^'+day+', \\d{2} '+month+' \\d{4} \\d{2}:\\d{2}:\\d{2} GMT$');
 const old=new RegExp('^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), \\d{2}-'+month+'-\\d{2} \\d{2}:\\d{2}:\\d{2} GMT$');
 const asc=new RegExp('^'+day+' '+month+' (?: \\d|\\d{2}) \\d{2}:\\d{2}:\\d{2} \\d{4}$');
 if(!imf.test(h)&&!old.test(h)&&!asc.test(h))return 0;
 // asctime has implicit GMT in HTTP, independent of the device's local zone.
 let input=asc.test(h)?h+' GMT':h;
 if(old.test(h)){
  const yy=Number(h.match(/-(\d{2}) /)[1]),currentYear=new Date(at).getUTCFullYear();
  let year=Math.floor(currentYear/100)*100+yy;if(year<=currentYear-50)year+=100;if(year>currentYear+50)year-=100;
  input=h.replace(/-(\d{2}) /,'-'+String(year).padStart(4,'0')+' ');
 }
 const date=Date.parse(input);
 if(!Number.isFinite(date))return 0;
 const parts=h.match(/(?:, )(\d{2})[ -]([A-Z][a-z]{2})[ -](\d{2,4}) (\d{2}:\d{2}:\d{2})/);
 const text=new Date(date).toUTCString();
 if(imf.test(h)&&text!==h)return 0;
 if(parts&&(!text.includes(parts[1]+' '+parts[2])||!text.includes(parts[4])))return 0;
 return Math.max(0,date-at);
}
async function withTraffic(action){
 try{return await navigator.locks.request(TRAFFIC_LOCK,{mode:'exclusive',ifAvailable:true},async lock=>{
  try{return await action(lock)}catch(e){
   // If possible, leave a persistent stop marker after clock/storage failure.
   // A denied write is never followed by a request from this document.
   if(lock&&['clock','storage'].includes(e.searchCode))try{
    const s=JSON.parse(localStorage.getItem(TRAFFIC_KEY));
    if(s?.version===1){s.cooldownUntil=null;localStorage.setItem(TRAFFIC_KEY,JSON.stringify(s))}
   }catch{}
   throw e;
  }
 })}catch(e){if(e.searchCode)throw e;throw searchError('unsupported','Safe search coordination unavailable')}
}
const cache=new Map(),pending=new Map();
async function fetchAttempt(address,entry,attempt,notify){
 const startedWaiting=performance.now(),controller=new AbortController();
 let timer,watcher,response,networkError;
 const check=()=>{
  if(entry.epoch!==epoch||document.hidden)throw searchError('background','Search interrupted in background; search again');
  if(!entry.hasCurrent())throw searchError('cancelled','Search superseded');
  now();
 };
 const stop=()=>{clearTimeout(timer);clearInterval(watcher);activeControllers.delete(controller)};
 try{
  if(!isSecureContext||!navigator.locks?.request)throw searchError('unsupported','Safe search coordination unavailable');
  for(;;){
   check();
   if(performance.now()-startedWaiting>=WAIT_LIMIT)throw searchError('waiting','Search coordination wait exceeded 30 seconds');
   let wait=100;
   // Polling ifAvailable keeps queued lock cancellation independent of browser support
   // for LockOptions.signal. No waiting/sleeping while holding the lock.
   const result=await withTraffic(async lock=>{
    if(!lock)return null;
    check();if(performance.now()-startedWaiting>=WAIT_LIMIT)throw searchError('waiting','Search coordination wait exceeded 30 seconds');
    const at=now(),s=readTraffic();
    if(s.lastStartAt>at+250)throw searchError('clock','Shared request time is in the future');
    if(s.cooldownUntil===null)throw searchError('cooldown','Server cooldown exceeds supported time range');
    const remaining=Math.max(s.lastStartAt? s.lastStartAt+INTERVAL-at:0,s.cooldownUntil-at,0);
    if(remaining>WAIT_LIMIT-(performance.now()-startedWaiting))throw searchError('cooldown','Search paused until server cooldown expires');
    if(remaining){wait=Math.min(remaining,100);notify({delay:remaining,waiting:true});return null}
    // A verified synchronous write immediately precedes fetch. No future reservation.
    s.lastStartAt=now();writeTraffic(s);check();
    activeControllers.add(controller);
    timer=setTimeout(()=>controller.abort(),20000);
    watcher=setInterval(()=>{try{check()}catch(e){controller.abort()}},100);
    try{
     const job=fetch(address,{headers:{Accept:'application/json'},signal:controller.signal});
     // Round conservatively after invocation, so storage overhead cannot shorten spacing.
     s.lastStartAt=now()+1;
     try{writeTraffic(s)}catch(e){controller.abort();job.catch(()=>{});throw e}
     response=await job;
    }catch(e){if(e.searchCode)throw e;networkError=e}
    // Persist before releasing, including on the fourth/final attempt and cancellation.
    const code=response?.status;
    if(clockFailed){s.cooldownUntil=null;writeTraffic(s);throw searchError('clock','Device clock changed; search paused')}
    if(networkError||retryable(code)){
     const at=Date.now(),delay=retryDelay(response?.headers.get('Retry-After'),at);
     const backoff=2000*Math.min(attempt+1,3);
     s.cooldownUntil=delay===null?null:Math.max(s.cooldownUntil,at+Math.max(backoff,delay));
     writeTraffic(s);
    }
    return {response,networkError};
   });
   if(!result){await sleep(wait);continue}
   check();
   // Headers and cooldown are settled; body decoding does not hold the Web Lock.
   let data;
   if(!networkError&&response.ok){try{data=await response.json()}catch(e){
    networkError=e;
    const began=performance.now();
    while(!await withTraffic(async lock=>{
     if(!lock)return false;
     const s=readTraffic(),at=now();
     if(s.cooldownUntil!==null)s.cooldownUntil=Math.max(s.cooldownUntil,at+2000*Math.min(attempt+1,3));
     writeTraffic(s);return true;
    })){
     if(performance.now()-began>=WAIT_LIMIT)throw searchError('waiting','Search cooldown publication timed out');
     await sleep(100);
    }
   }}
   check();
   return {response,data,networkError};
  }
 }finally{stop()}
}
function request(address,ctx){
 current(ctx);
 const hit=cache.get(address);
 if(hit&&Date.now()-hit.at<CACHE_MS)return Promise.resolve(hit.data);
 if(hit)cache.delete(address);
 if(pending.has(address)){const active=pending.get(address);active.listeners.add(ctx||{});return active.job}
 const entry={listeners:new Set([ctx||{}]),epoch,queuedAt:performance.now()};
 entry.hasCurrent=()=>[...entry.listeners].some(c=>!c.isCurrent||c.isCurrent());
 const notify=notice=>{for(const c of entry.listeners)if(!c.isCurrent||c.isCurrent()){if(notice.waiting)c.onWait?.(notice);else c.onRetry?.(notice)}};
 entry.job=queue.catch(()=>{}).then(async()=>{
  if(performance.now()-entry.queuedAt>=WAIT_LIMIT)throw searchError('waiting','Search queue wait exceeded 30 seconds');
  for(let attempt=0;attempt<4;attempt++){
   const {response,data,networkError}=await fetchAttempt(address,entry,attempt,notify);
   if(!networkError&&response.ok){cache.set(address,{data,at:Date.now()});if(cache.size>CACHE_LIMIT)cache.delete(cache.keys().next().value);return data}
   const code=response?.status;
   if(attempt===3||(!networkError&&!retryable(code)))throw new Error(networkError?'Network error / timeout':`MusicBrainz HTTP ${code}`);
   notify({code:networkError?null:code,attempt:attempt+1,delay:2000*(attempt+1)});
  }
 });
 queue=entry.job.catch(()=>{});pending.set(address,entry);
 entry.job.finally(()=>pending.delete(address)).catch(()=>{});
 return entry.job;
}
async function artistSearch(q,ctx){
  const term=norm(q),n=searchNorm(term);if(!n)return [];
  const variants=[...new Set([term,hira(term),kata(term)])],fields=['artist','alias','sortname'];
  const quality=a=>artistQuality(q,a);
  const ordered=arr=>unique(arr).filter(a=>quality(a)).sort((a,b)=>quality(b)-quality(a)||Number(b.score||0)-Number(a.score||0));
  const quoted=variants.map(v=>'('+fields.map(f=>`${f}:"${escape(v)}"`).join(' OR ')+')').join(' OR ');
  let raw=(await request(url('artist/',{query:quoted,limit:100}),ctx)).artists||[];current(ctx);
  if(!raw.some(a=>quality(a))&&n.length>=2){
    const prefix=variants.map(v=>'('+v.split(/\s+/).filter(Boolean).map(w=>'('+fields.map(f=>`${f}:${escape(w)}*`).join(' OR ')+')').join(' AND ')+')').join(' OR ');
    raw=unique([...raw,...((await request(url('artist/',{query:prefix,limit:100}),ctx)).artists||[])]);current(ctx);
  }
  if(raw.some(a=>quality(a)===3))return ordered(raw);
  const detailed=raw.filter(a=>quality(a));
  for(const a of raw.sort((a,b)=>Number(b.score||0)-Number(a.score||0)).slice(0,15)){
    let v=a;
    if(!Array.isArray(a.aliases)){
      const details=await request(url('artist/'+encodeURIComponent(a.id),{inc:'aliases'}),ctx);current(ctx);
      v={...a,...details,score:a.score};
    }
    if(quality(v)){const i=detailed.findIndex(x=>x.id===v.id);if(i>=0)detailed[i]=v;else detailed.push(v)}
  }
  // A server score alone cannot establish an artist match (e.g. a band containing a person's name).
  return ordered(detailed);
}
async function browseArtist(id,ctx){
  let all=[],offset=0;
  for(;;){
    const data=await request(url('release-group/',{artist:id,inc:'artist-credits',limit:100,offset}),ctx);current(ctx);
    const raw=data['release-groups']||[];all.push(...raw);offset+=raw.length;
    const total=Number(data['release-group-count']??data.count);
    if(!raw.length||(Number.isFinite(total)?offset>=total:raw.length<100))break;
  }
  return unique(all).filter(r=>rank(r)<3).sort(sort);
}
async function titlePage(q,offset=0,ctx){
  const query=`releasegroup:"${escape(q.trim())}" AND (primarytype:album OR primarytype:ep OR primarytype:single)`;
  const data=await request(url('release-group/',{query,limit:100,offset}),ctx);current(ctx);
  const raw=data['release-groups']||[],next=offset+raw.length,total=Number(data.count??data['release-group-count']);
  const items=sortTitles(unique(raw),q);
  return {items,offset:next,exhausted:!raw.length||(Number.isFinite(total)?next>=total:raw.length<100)};
}
async function start(q,ctx,mode='auto'){
  if(mode==='title')return {mode:'title',...(await titlePage(q,0,ctx))};
  const artists=await artistSearch(q,ctx);current(ctx);
  const exact=artists.filter(a=>artistQuality(q,a)===3),choices=exact.length?exact:artists;
  if(choices.length>1)return {mode:'candidates',candidates:choices,items:[],offset:0,exhausted:true};
  if(choices.length)return {mode:'artist',artist:choices[0],items:await browseArtist(choices[0].id,ctx),offset:0,exhausted:true};
  if(mode==='artist')return {mode:'artist',items:[],offset:0,exhausted:true};
  return {mode:'title',...(await titlePage(q,0,ctx))};
}
async function ensureCredit(r,ctx){
  if(credit(r))return r;
  const details=await request(url('release-group/'+encodeURIComponent(r.id),{inc:'artist-credits'}),ctx);current(ctx);
  return {...r,...details};
}
window.MMASearch={request,artistSearch,browseArtist,titlePage,start,ensureCredit,credit,unique,sort,sortTitles,searchNorm};
})();

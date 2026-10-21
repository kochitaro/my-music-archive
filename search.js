/* MusicBrainz search shared by MMA and Search Lab. No browser storage writes. */
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
let queue=Promise.resolve(),lastCall=0;
const cache=new Map(),pending=new Map();
function request(address,ctx){
  current(ctx);
  const hit=cache.get(address);
  if(hit&&Date.now()-hit.at<CACHE_MS)return Promise.resolve(hit.data);
  if(hit)cache.delete(address);
  if(pending.has(address)){
    const active=pending.get(address);active.listeners.add(ctx||{});return active.job;
  }
  const entry={listeners:new Set([ctx||{}])};
  const notify=notice=>{for(const listener of entry.listeners)if(!listener.isCurrent||listener.isCurrent())listener.onRetry?.(notice)};
  entry.job=queue.catch(()=>{}).then(async()=>{
    for(let attempt=0;attempt<4;attempt++){
      // Stale queued searches need no new API call. A deduplicated current caller can keep it alive.
      if(entry.listeners.size&&![...entry.listeners].some(c=>!c.isCurrent||c.isCurrent()))throw new Error('Search superseded');
      const interval=Math.max(0,1250-(Date.now()-lastCall));if(interval)await sleep(interval);
      const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000);
      let response,data,networkError;
      lastCall=Date.now();
      try{response=await fetch(address,{headers:{Accept:'application/json'},signal:controller.signal});if(response.ok)data=await response.json()}
      catch(e){networkError=e}finally{clearTimeout(timer)}
      if(!networkError&&response.ok){
        cache.set(address,{data,at:Date.now()});
        if(cache.size>CACHE_LIMIT)cache.delete(cache.keys().next().value);
        return data;
      }
      const code=response?.status;
      if(attempt===3||(!networkError&&![429,502,503,504].includes(code)))throw new Error(networkError?'Network error / timeout':`MusicBrainz HTTP ${code}`);
      const header=response?.headers.get('Retry-After')?.trim();
      const retryAfter=header&&/^\d+(?:\.\d+)?$/.test(header)?Number(header)*1000:0;
      // Honour the server's numeric Retry-After, including values above the Lab's old 15s cap.
      const delay=Math.max(2000*(attempt+1),Number.isFinite(retryAfter)?retryAfter:0);
      notify({code:networkError?null:code,attempt:attempt+1,delay});await sleep(delay);
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
  const items=unique(raw).sort((a,b)=>Number(searchNorm(b.title)===searchNorm(q))-Number(searchNorm(a.title)===searchNorm(q))||Number(b.score||0)-Number(a.score||0));
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
window.MMASearch={request,artistSearch,browseArtist,titlePage,start,ensureCredit,credit,unique,sort,searchNorm};
})();

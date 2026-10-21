const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const source=fs.readFileSync(require.resolve('../search.js'),'utf8');
const artists=require('./fixtures/artists.json');
const credits=require('./fixtures/credits.json');
function harness(handler,timeouts=false){
 let now=1000000,active=0,maxActive=0;
 const calls=[],delays=[];
 const context={window:{},URLSearchParams,AbortController,Date:{now:()=>now},
  setTimeout:(fn,ms)=>{if(String(fn).includes("controller.abort"))return timeouts?setTimeout(fn,0):null;delays.push(ms);now+=ms;return setTimeout(fn,0)},clearTimeout,
  fetch:async(address,options)=>{calls.push({url:new URL(address),at:now});active++;maxActive=Math.max(maxActive,active);try{return await handler(new URL(address),calls.length,options)}finally{active--}}
 };
 vm.runInNewContext(source,context);
 return {api:context.window.MMASearch,calls,delays,advance:ms=>now+=ms,maxActive:()=>maxActive};
}
const response=(data={},status=200,retryAfter=null)=>({ok:status===200,status,headers:{get:()=>retryAfter},json:async()=>structuredClone(data)});
for(const code of [429,502,503,504,'network'])test(`${code}: max four attempts, notices, spacing, then queue recovers`,async()=>{
 const notices=[];
 const h=harness((u,n)=>{if(u.pathname.endsWith('/bad')){if(code==='network')throw Error('offline');return response({},code)}return response({ok:true})});
 await assert.rejects(h.api.request('https://example.test/bad',{onRetry:n=>notices.push(n)}));
 assert.equal(h.calls.length,4);assert.equal(notices.length,3);
 for(let i=1;i<4;i++)assert.ok(h.calls[i].at-h.calls[i-1].at>=1250);
 assert.equal((await h.api.request('https://example.test/good')).ok,true);
});
test('Retry-After is honoured above 15 seconds, malformed values use backoff',async()=>{
 for(const header of ['20','1.5','Wed, 21 Oct 2026 12:00:00 GMT','garbage']){
  const h=harness((u,n)=>response({},n===1?503:200,header));await h.api.request('https://example.test/a');
  assert.equal(h.calls[1].at-h.calls[0].at,header==='20'?20000:2000);
 }
});
test('non-retryable HTTP errors and failed body reads',async()=>{
 const bad=harness(()=>response({},400));await assert.rejects(bad.api.request('https://example.test/a'));assert.equal(bad.calls.length,1);
 const body=harness((u,n)=>n===1?{...response(),json:async()=>{throw Error('disconnected body')}}:response({ok:true}));assert.equal((await body.api.request('https://example.test/a')).ok,true);assert.equal(body.calls.length,2);
});
test('serialized requests, in-flight deduplication, five-minute cache expiry',async()=>{
 const h=harness(async()=>{await new Promise(r=>setTimeout(r,1));return response({ok:true})});
 const [a,b]=await Promise.all([h.api.request('https://example.test/a'),h.api.request('https://example.test/a'),h.api.request('https://example.test/b')]);
 assert.equal(a,b);assert.equal(h.calls.length,2);assert.equal(h.maxActive(),1);assert.ok(h.calls[1].at-h.calls[0].at>=1250);
 await h.api.request('https://example.test/a');assert.equal(h.calls.length,2);
 h.advance(300001);await h.api.request('https://example.test/a');assert.equal(h.calls.length,3);
});
test('stale requests skip queued calls; deduplicated current caller receives retry notice',async()=>{
 let active=true;const stale=[],current=[];
 const h=harness((u,n)=>response({},n===1?503:200));
 const old=h.api.request('https://example.test/a',{isCurrent:()=>active,onRetry:n=>stale.push(n)});
 active=false;const next=h.api.request('https://example.test/a',{isCurrent:()=>true,onRetry:n=>current.push(n)});
 await Promise.all([old,next]);assert.equal(stale.length,0);assert.equal(current.length,1);
 assert.throws(()=>h.api.request('https://example.test/stale',{isCurrent:()=>false})); // request itself rejects a stale caller synchronously
});
for(const [query,id] of [['Number Girl','808fe413-ff00-4a68-99fe-0ab265a7e2be'],['ナンバーガール','808fe413-ff00-4a68-99fe-0ab265a7e2be'],['細野晴臣','078be324-de92-4c72-9371-65bdcf324154'],['Haruomi Hosono','078be324-de92-4c72-9371-65bdcf324154']])test(`actual API artist fixture: ${query}`,async()=>{
 const h=harness(()=>response(artists[query]));const found=await h.api.artistSearch(query);assert.equal(found[0].id,id);assert.equal(h.calls.length,1);
});
test('kana normalization, alias sort names, and name agreement outrank server score',async()=>{
 const h=harness(()=>response(artists['ナンバーガール']));assert.equal((await h.api.artistSearch('なんばーがーる'))[0].id,artists['ナンバーガール'].artists[0].id);
 const hosono=harness(()=>response(artists['Haruomi Hosono']));assert.equal((await hosono.api.artistSearch('ホソノ ハルオミ'))[0].id,'078be324-de92-4c72-9371-65bdcf324154');
});
test('missing aliases are enriched; high-score unrelated artists fall back to title search',async()=>{
 const h=harness(u=>u.pathname.includes('/artist/x')?response({name:'English',aliases:[{name:'日本語'}]}):response({artists:[{id:'x',name:'English',score:100}]}));
 assert.equal((await h.api.artistSearch('日本語'))[0].id,'x');assert.ok(h.calls.some(c=>c.url.searchParams.get('inc')==='aliases'));
 const fallback=harness(u=>u.pathname.includes('/artist/')?response({artists:[{id:'wrong',name:'Unrelated',score:100,aliases:[]}]}):response({count:1,'release-groups':[{id:'r',title:'Album', 'primary-type':'Album'}]}));
 const result=await fallback.api.start('Album');assert.equal(result.mode,'title');assert.equal(result.items[0].id,'r');
});
test('browse consumes more than 600 raw records, sorts entire catalog, deduplicates by MBID',async()=>{
 const rows=Array.from({length:705},(_,i)=>({id:String(i),title:'Work '+i,'primary-type':['Single','EP','Album','Other'][i%4],'first-release-date':String(1900+i),'artist-credit':[{name:'Artist'}]}));rows[101]=rows[0];
 const h=harness(u=>{assert.equal(u.searchParams.get('inc'),'artist-credits');const offset=Number(u.searchParams.get('offset'));return response({'release-group-count':rows.length,'release-groups':rows.slice(offset,offset+100)})});
 const all=await h.api.browseArtist('x');assert.equal(h.calls.length,8);assert.equal(all.length,new Set(rows.filter(r=>['Album','EP','Single'].includes(r['primary-type'])).map(r=>r.id)).size);
 assert.equal(all[0].id,'702');const types=all.map(r=>r['primary-type']);assert.ok(types.lastIndexOf('Album')<types.indexOf('EP'));assert.ok(types.lastIndexOf('EP')<types.indexOf('Single'));
});
test('title pagination uses raw offsets and count, not displayed/deduplicated length',async()=>{
 const h=harness(u=>{const off=Number(u.searchParams.get('offset'));return response({count:105,'release-groups':Array.from({length:off?5:100},(_,i)=>({id:String(off+i),title:'Title'}))})});
 const a=await h.api.titlePage('A + "B"');assert.equal(a.offset,100);assert.equal(a.exhausted,false);assert.ok(h.calls[0].url.searchParams.get('query').includes('\\+'));
 const b=await h.api.titlePage('A + "B"',a.offset);assert.equal(b.offset,105);assert.equal(b.exhausted,true);
});
test('actual Unknown Artist reproduction and credit repair preserve credited name and joinphrases',async()=>{
 const h=harness(()=>response(credits['with-credit']));assert.equal(h.api.credit(credits['without-credit']),'');
 const fixed=await h.api.ensureCredit(credits['without-credit']);assert.equal(h.api.credit(fixed),'Haruomi Hosono & Yasuhiko Terada');assert.equal(h.calls.length,1);
 await h.api.ensureCredit(fixed);assert.equal(h.calls.length,1);
 assert.equal(h.api.credit({'artist-credit':[{name:'A',joinphrase:' & '},{artist:{name:'B'},joinphrase:' feat. '},'C']}),'A & B feat. C');
});

test('a timed-out fetch aborts, retries, and recovers',async()=>{
 let aborted=false;
 const h=harness((u,n,options)=>n===1?new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>{aborted=true;reject(Error('timeout'))})):response({ok:true}),true);
 assert.equal((await h.api.request('https://example.test/timeout')).ok,true);assert.equal(aborted,true);assert.equal(h.calls.length,2);
});

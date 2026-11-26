// Deterministic failure/expiry tests. Real 1250ms timing is covered by transport_browser.cjs.
const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync(require.resolve('../search.js'),'utf8'),KEY='mla:musicbrainz:traffic:v1';
function harness(handler,options={}){
 let time=1_000_000,offset=0,held=false,failWrite=false;
 const storage=new Map(),calls=[],events={},windowEvents={},notices=[];
 const context={window:{addEventListener:(k,f)=>windowEvents[k]=f},document:{hidden:false,addEventListener:(k,f)=>events[k]=f},
  navigator:{locks:{request:async(k,o,f)=>{assert.equal(k,'mla:musicbrainz:request:v1');assert.equal(o.ifAvailable,true);held=true;try{return await f({})}finally{held=false}}}},
  localStorage:{getItem:k=>storage.get(k)??null,setItem:(k,v)=>{if(failWrite)throw Error('quota');storage.set(k,v)}},
  isSecureContext:true,Date:class extends Date{static now(){return time+offset}},performance:{now:()=>time},
  URLSearchParams,AbortController,setInterval:()=>null,clearInterval(){},clearTimeout,
  setTimeout:(f,ms)=>{if(ms===20000)return null;time+=ms;options.onSleep?.(ms);return setTimeout(f,0)},
  fetch:async(u,o)=>{calls.push({u,at:time});return handler(u,calls.length,o,()=>held)}
 };
 vm.runInNewContext(source,context);
 return {api:context.window.MMASearch,storage,calls,context,notices,ctx:{onRetry:n=>notices.push(n)},
  advance:ms=>time+=ms,jump:ms=>offset+=ms,failWrite:()=>failWrite=true,
  hide:()=>{context.document.hidden=true;events.visibilitychange()},show:()=>context.document.hidden=false,
  state:()=>JSON.parse(storage.get(KEY))};
}
const reply=(status=200,header=null,json=async()=>({ok:true}))=>({ok:status===200,status,headers:{get:()=>header},json});
test('all four attempts; final failure publishes cooldown before a different URL',async()=>{
 const h=harness((u)=>reply(u==='bad'?503:200));await assert.rejects(h.api.request('bad',h.ctx));
 assert.deepEqual(h.calls.map(c=>c.at),[1000000,1002000,1006000,1012000]);assert.equal(h.state().cooldownUntil,1018000);
 await h.api.request('next');assert.equal(h.calls[4].at,1018000);assert.equal(h.notices.length,3);
});
for(const [name,header,delay] of [['seconds','20',20000],['decimal','2.0001',2001],['IMF','Thu, 01 Jan 1970 00:17:00 GMT',20000],['RFC850','Thursday, 01-Jan-70 00:17:00 GMT',20000],['asctime','Thu Jan  1 00:17:00 1970',20000],['past','Thu, 01 Jan 1970 00:00:00 GMT',2000],['malformed','tomorrow',2000],['negative','-10',2000],['missing',null,2000]])test(name+' Retry-After',async()=>{
 const h=harness((u,n)=>reply(n===1?503:200,header));await h.api.request('a');assert.equal(h.calls[1].at-h.calls[0].at,delay);
});
for(const header of ['31','9'.repeat(400)])test('long/overflow delay ends search and persists suppression: '+header.slice(0,8),async()=>{
 const h=harness(()=>reply(429,header));await assert.rejects(h.api.request('a'),e=>e.searchCode==='cooldown');assert.equal(h.calls.length,1);
 const state=h.state();assert.equal(state.cooldownUntil,header==='31'?1031000:null);
 await assert.rejects(h.api.request('b'),e=>e.searchCode==='cooldown');assert.equal(h.calls.length,1);assert.deepEqual(h.state(),state);
});
test('corrupt state, removed state, denied writes and missing locks fail closed',async()=>{
 for(const raw of ['{','{}','null','{"version":2,"lastStartAt":0,"cooldownUntil":0}']){
  const h=harness(()=>reply());h.storage.set(KEY,raw);await assert.rejects(h.api.request('a'),e=>e.searchCode==='storage');assert.equal(h.calls.length,0);
 }
 const h=harness(()=>reply());h.failWrite();await assert.rejects(h.api.request('a'),e=>e.searchCode==='storage');assert.equal(h.calls.length,0);
 const missing=harness(()=>reply());delete missing.context.navigator.locks;await assert.rejects(missing.api.request('a'),e=>e.searchCode==='unsupported');assert.equal(missing.calls.length,0);
 const removed=harness(()=>reply());await removed.api.request('a');removed.storage.delete(KEY);await assert.rejects(removed.api.request('b'),e=>e.searchCode==='storage');assert.equal(removed.calls.length,1);
});
test('a wall-clock jump stops traffic instead of expiring cooldown early',async()=>{
 for(const offset of [-60000,60000]){const h=harness(()=>reply());await h.api.request('a');h.jump(offset);await assert.rejects(h.api.request('b'),e=>e.searchCode==='clock');assert.equal(h.calls.length,1)}
});
test('body parsing does not hold traffic lock',async()=>{
 const h=harness((u,n,o,held)=>reply(200,null,async()=>{assert.equal(held(),false);return {ok:true}}));await h.api.request('a');
});
test('cancelled cooldown wait preserves deadline and a deduplicated current listener',async()=>{
 let valid=true,h;h=harness((u,n)=>reply(n===1?503:200,'4'),{onSleep:()=>valid=false});
 const old=h.api.request('a',{isCurrent:()=>valid}),current=h.api.request('a',{isCurrent:()=>true});await Promise.all([old,current]);assert.equal(h.calls.length,2);assert.equal(h.calls[1].at,1004000);
 let cancelled=true;const c=harness(()=>reply(503,'4'),{onSleep:()=>cancelled=false});await assert.rejects(c.api.request('a',{isCurrent:()=>cancelled}));assert.equal(c.calls.length,1);assert.equal(c.state().cooldownUntil,1004000);
});
test('background cancellation retains shared cooldown, query ownership is not reset',async()=>{
 let h,hidden=false;h=harness(()=>reply(503,'4'),{onSleep:()=>{if(!hidden){hidden=true;h.hide()}}});await assert.rejects(h.api.request('a'),e=>e.searchCode==='background');assert.equal(h.calls.length,1);assert.equal(h.state().cooldownUntil,1004000);
 h.show();await assert.rejects(h.api.request('b'));assert.equal(h.calls[1].at,1004000);
});
test('busy lock has a 30s active waiting limit and never sends unprotected',async()=>{
 const h=harness(()=>reply());h.context.navigator.locks.request=async(k,o,f)=>f(null);
 await assert.rejects(h.api.request('a'),e=>e.searchCode==='waiting');assert.equal(h.calls.length,0);
});

test('invalid calendar date falls back; RFC850 century obeys the HTTP 50-year rule',async()=>{
 const invalid=harness((u,n)=>reply(n===1?503:200,'Thu, 31 Feb 1970 00:17:00 GMT'));await invalid.api.request('a');assert.equal(invalid.calls[1].at-invalid.calls[0].at,2000);
 const future=harness(()=>reply(503,'Tuesday, 01-Jan-20 00:00:00 GMT'));await assert.rejects(future.api.request('a'),e=>e.searchCode==='cooldown');assert.equal(future.calls.length,1);
});
test('failure to publish a response cooldown stops this document before another fetch',async()=>{
 let h;h=harness(()=>{h.failWrite();return reply(503,'20')});await assert.rejects(h.api.request('a'),e=>e.searchCode==='storage');
 await assert.rejects(h.api.request('b'),e=>e.searchCode==='storage');assert.equal(h.calls.length,1);
});
test('unavailable reads stop search and body-read final errors retain cooldown',async()=>{
 const unavailable=harness(()=>reply());unavailable.context.localStorage.getItem=()=>{throw Error('denied')};await assert.rejects(unavailable.api.request('a'),e=>e.searchCode==='storage');assert.equal(unavailable.calls.length,0);
 const body=harness(()=>reply(200,null,async()=>{throw Error('truncated body')}));await assert.rejects(body.api.request('a'));assert.equal(body.calls.length,4);assert.equal(body.state().cooldownUntil,1018000);
});

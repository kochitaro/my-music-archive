// Synthetic timing model, never sends network requests. Run with SEARCH_SOURCE for baseline.
const fs=require('node:fs'),vm=require('node:vm'),{performance}=require('node:perf_hooks');
const source=fs.readFileSync(process.env.SEARCH_SOURCE||'search.js','utf8');
async function scenario(name,mode,opts={}){
 let now=1000000,interval=0,retry=0,network=0,parse=0,live=true;
 const calls=[],cpu=[];
 const rows=Array.from({length:100},(_,i)=>({id:String(i),title:'Work '+i,'primary-type':'Album','artist-credit':[{name:'Twin'}]}));
 const ctx={isCurrent:()=>live};
 const sandbox={window:{},URLSearchParams,AbortController,Date:{now:()=>now},clearTimeout,
 setTimeout:(fn,ms)=>{if(String(fn).includes('controller.abort'))return null;now+=ms;if(ms<2000){interval+=ms;if(opts.cancel)live=false}else retry+=ms;return setTimeout(fn,0)},
 fetch:async address=>{const u=new URL(address);calls.push({path:u.pathname,at:now});network+=250;now+=250;
 const failed=opts.fail&&calls.length===1;
 return {ok:!failed,status:failed?503:200,headers:{get:()=>opts.header||null},json:async()=>{parse+=5;now+=5;return u.pathname.includes('/artist/')?{artists:[{id:'a',name:'Twin',aliases:[]},...(opts.choices?[{id:'b',name:'Twin',aliases:[]}]:[])]}:{count:100,'release-group-count':100,'release-groups':rows}}};}};
 vm.runInNewContext(source,sandbox);const api=sandbox.window.MMASearch;
 const run=async()=>{const before=performance.now();try{return mode==='browse'?await api.browseArtist('a',ctx):await api.start('Twin',ctx,mode)}finally{cpu.push(performance.now()-before)}};
 if(opts.cancel)await api.request('https://example.test/warm');
 const start=now,initial={interval,retry,network,parse,calls:calls.length};let result,error;try{result=await run();if(opts.repeat){const t=now;result=await run();opts.repeatMs=now-t}}catch(e){error=e.message}
 const elapsed=now-start,obsoleteCalls=calls.length-initial.calls;let recoveryMs;
 if(opts.cancel){live=true;const t=now;await api.request('https://example.test/current');recoveryMs=now-t}
 return {name,modelElapsedMs:elapsed,recoveryMs,totalThroughRecoveryMs:opts.cancel?now-start:undefined,obsoleteCalls:opts.cancel?obsoleteCalls:undefined,intervalMs:interval-initial.interval,retryMs:retry-initial.retry,apiMs:network-initial.network,jsonMs:parse-initial.parse,calls:calls.length-initial.calls,repeatMs:opts.repeatMs,error,items:result?.items?.length,mode:result?.mode,wallMs:cpu};
}
(async()=>{const out=[];for(const [n,m,o] of [['artist cold','artist',{}],['title cold','title',{}],['artist repeated','artist',{repeat:true}],['title repeated','title',{repeat:true}],['artist candidates','artist',{choices:true}],['selected artist catalog','browse',{}],['503 then success','title',{fail:true}],['Retry-After 5s','title',{fail:true,header:'5'}],['switch during interval','title',{cancel:true}]])out.push(await scenario(n,m,o));console.log(JSON.stringify({environment:'Node VM, virtual time; API 250ms + JSON 5ms per success, no real API calls; wall includes timer scheduling',results:out},null,2))})();

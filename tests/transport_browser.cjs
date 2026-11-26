/* Mock HTTP only. No external requests, no shortened clocks or 1250ms intervals.
 * node tests/transport_browser.cjs chromium|firefox|webkit [evidence.json]
 */
const http=require('node:http'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium,firefox,webkit}=require('playwright');
const ROOT=path.resolve(__dirname,'..'),KEY='mla:musicbrainz:traffic:v1',browserName=process.argv[2]||'chromium';
const received=[],checks=[],timing=[],contexts=[],counts=new Map();
const start=server=>new Promise(r=>server.listen(0,'127.0.0.1',()=>r(`http://127.0.0.1:${server.address().port}`)));
const handler=(q,s)=>{
 const u=new URL(q.url,'http://localhost');
 if(u.pathname.startsWith('/api/')){
  const key=u.pathname+u.search,n=(counts.get(key)||0)+1;counts.set(key,n);
  received.push({url:key,method:q.method,at:performance.timeOrigin+performance.now(),ua:q.headers['user-agent']});
  s.setHeader('Access-Control-Allow-Origin','*');s.setHeader('Content-Type','application/json');
  let status=200,header;
  if(u.pathname==='/api/retry'&&n===1){status=503;header='2'}
  if(u.pathname==='/api/date'&&n===1){status=503;header=new Date(Date.now()+4000).toUTCString()}
  if(u.pathname==='/api/hidden'&&n===1){status=503;header='10'}
  if(u.pathname==='/api/always'){status=503;header='2'}
  if(u.pathname==='/api/long'){status=429;header='31'}
  if(u.pathname==='/api/overflow'){status=503;header='9'.repeat(400)}
  if(u.pathname==='/api/timeout'&&n===1)return;
  if(header)s.setHeader('Retry-After',header);
  if(u.pathname!=='/api/hidden')s.setHeader('Access-Control-Expose-Headers','Retry-After');
  s.writeHead(status);
  if(u.pathname==='/api/slow')setTimeout(()=>s.end('{"ok":true}'),1500);
  else s.end('{"ok":true}');return;
 }
 if(u.pathname==='/probe'){s.setHeader('Content-Type','text/html');s.end('<!doctype html><script src="/search.js"></script>');return}
 let file=path.resolve(ROOT,'.'+(u.pathname==='/'?'/index.html':u.pathname));
 if(!file.startsWith(ROOT+path.sep)){s.writeHead(403);s.end();return}
 try{s.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html');s.end(fs.readFileSync(file))}catch{s.writeHead(404);s.end()}
};
const server=http.createServer(handler),cors=http.createServer(handler);
(async()=>{
 const base=await start(server),other=await start(cors);let browser;
 const pass=(name,details={})=>{checks.push({name,...details});console.log('PASS',name,JSON.stringify(details))};
 try{
  browser=await ({chromium,firefox,webkit})[browserName].launch(browserName==='chromium'?{executablePath:process.env.MMA_CHROMIUM||'/usr/bin/chromium',args:['--no-sandbox']}:{ });
  async function group(name,tabs=1,init){
   const c=await browser.newContext();contexts.push(c);
   await c.route(/^https?:\/\/(?!127\.0\.0\.1:\d+\/)/,r=>r.abort());
   await c.addInitScript(()=>{const native=fetch;globalThis.starts=[];globalThis.fetch=(...a)=>{starts.push({url:String(a[0]),at:performance.timeOrigin+performance.now()});return native(...a)}});
   if(init)await c.addInitScript(init);
   const pages=[];for(let i=0;i<tabs;i++){const p=await c.newPage();await p.goto(base+'/probe');pages.push(p)}
   return {c,pages,name};
  }
  const call=(p,url)=>p.evaluate(async u=>{try{return {data:await MMASearch.request(u)}}catch(e){return {error:e.searchCode||e.message}}},url);
  async function measure(g){
   const sent=(await Promise.all(g.pages.filter(p=>!p.isClosed()).map(p=>p.evaluate(()=>starts)))).flat().sort((a,b)=>a.at-b.at);
   const recv=received.filter(x=>x.url.includes('g='+g.name)).sort((a,b)=>a.at-b.at);
   const deltas=sent.slice(1).map((x,i)=>x.at-sent[i].at),wire=recv.slice(1).map((x,i)=>x.at-recv[i].at);
   assert(deltas.every(x=>x>=1250),JSON.stringify({name:g.name,deltas}));
   const data={group:g.name,fetchStarts:sent,received:recv,minFetchMs:deltas.length?Math.min(...deltas):null,minReceiveMs:wire.length?Math.min(...wire):null};timing.push(data);return data;
  }
  // Five tabs, two URLs each, including a retry. All paths share one lock/state.
  let g=await group('five',5);
  await Promise.all(g.pages.map((p,i)=>p.evaluate(async({base,i})=>{for(const [step,kind] of [i===0?'retry':'ok','ok'].entries())await MMASearch.request(`${base}/api/${kind}?g=five&i=${i}&step=${step}`)}, {base,i})));
  let m=await measure(g);assert.equal(m.fetchStarts.length,11);pass('five simultaneous tabs, retry, real spacing',{minFetchMs:m.minFetchMs,minReceiveMs:m.minReceiveMs});await g.c.close();
  g=await group('two',2);await Promise.all(g.pages.map((p,i)=>call(p,base+'/api/ok?g=two&i='+i)));m=await measure(g);pass('two simultaneous tabs',{minFetchMs:m.minFetchMs});await g.c.close();
  g=await group('date');assert((await call(g.pages[0],base+'/api/date?g=date')).data);m=await measure(g);assert(m.minFetchMs>=2900);pass('HTTP-date not shortened',{minFetchMs:m.minFetchMs});await g.c.close();
  g=await group('hidden');assert((await call(g.pages[0],other+'/api/hidden?g=hidden')).data);m=await measure(g);assert(m.minFetchMs>=2000&&m.minFetchMs<10000);pass('CORS-hidden Retry-After uses backoff',{minFetchMs:m.minFetchMs});await g.c.close();
  g=await group('final',2);assert((await call(g.pages[0],base+'/api/always?g=final')).error);const state=await g.pages[1].evaluate(k=>JSON.parse(localStorage.getItem(k)),KEY);await g.pages[1].reload();assert((await call(g.pages[1],base+'/api/ok?g=final')).data);m=await measure(g);assert.equal(m.fetchStarts.length,5);assert(m.fetchStarts[4].at>=state.cooldownUntil);pass('four attempts; final cooldown survives another URL/tab/reload',{cooldownUntil:state.cooldownUntil,lastStart:m.fetchStarts[4].at});await g.c.close();
  for(const name of ['long','overflow']){
   g=await group(name,2);const result=await call(g.pages[0],base+`/api/${name}?g=${name}`);assert.equal(result.error,'cooldown');const state=await g.pages[0].evaluate(k=>localStorage.getItem(k),KEY);await g.pages[1].reload();assert.equal((await call(g.pages[1],base+`/api/ok?g=${name}`)).error,'cooldown');assert.equal(await g.pages[1].evaluate(k=>localStorage.getItem(k),KEY),state);m=await measure(g);assert.equal(m.fetchStarts.length,1);pass(name+' suppresses other tab and reload without shortening');await g.c.close();
  }
  g=await group('cancel');const p=g.pages[0];await call(p,base+'/api/ok?g=cancel&seed=1');const result=await p.evaluate(async base=>{
   let old=true;const a=MMASearch.request(base+'/api/ok?g=cancel&dedup=1',{isCurrent:()=>old}),b=MMASearch.request(base+'/api/ok?g=cancel&dedup=1',{isCurrent:()=>true});old=false;await Promise.all([a,b]);
   let valid=true;const cancelled=MMASearch.request(base+'/api/ok?g=cancel&obsolete=1',{isCurrent:()=>valid}).catch(e=>e.searchCode);setTimeout(()=>valid=false,100);return await cancelled;
  },base);assert.equal(result,'cancelled');m=await measure(g);assert.equal(m.fetchStarts.length,2);pass('cancel waiting search, keep valid deduplicated listener');await g.c.close();
  g=await group('close',2);await g.pages[0].evaluate(base=>{MMASearch.request(base+'/api/timeout?g=close').catch(()=>{})},base);while(!received.some(x=>x.url==='/api/timeout?g=close'))await new Promise(r=>setTimeout(r,20));await g.pages[0].close();assert((await call(g.pages[1],base+'/api/ok?g=close')).data);assert.equal(await g.pages[1].evaluate(()=>navigator.locks.query().then(x=>x.held.length)),0);pass('tab closure during fetch releases lock');await g.c.close();
  g=await group('busylock',2);await g.pages[0].evaluate(()=>{navigator.locks.request('mla:musicbrainz:request:v1',()=>new Promise(r=>globalThis.releaseTraffic=r))});await g.pages[0].waitForFunction(()=>!!globalThis.releaseTraffic);const waitBegan=Date.now();assert.equal((await call(g.pages[1],base+'/api/ok?g=busylock')).error,'waiting');assert(Date.now()-waitBegan>=30000);await g.pages[0].evaluate(()=>releaseTraffic());assert.equal((await measure(g)).fetchStarts.length,0);pass('real 30-second lock wait stops without unprotected fetch');await g.c.close();
  g=await group('timeout');assert((await call(g.pages[0],base+'/api/timeout?g=timeout')).data);m=await measure(g);assert(m.minFetchMs>=22000);pass('real 20-second abort then backoff/retry',{minFetchMs:m.minFetchMs});await g.c.close();
  g=await group('background');await call(g.pages[0],base+'/api/ok?g=background&seed=1');const bg=await g.pages[0].evaluate(async base=>{const job=MMASearch.request(base+'/api/ok?g=background&old=1').catch(e=>e.searchCode);Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));const result=await job;Object.defineProperty(document,'hidden',{configurable:true,value:false});return result},base);assert.equal(bg,'background');assert((await call(g.pages[0],base+'/api/ok?g=background&new=1')).data);m=await measure(g);assert.equal(m.fetchStarts.length,2);pass('synthetic hidden/restore discards old task and permits explicit re-search');await g.c.close();
  for(const fault of ['corrupt','write','locks']){
   g=await group('fault-'+fault);await g.pages[0].evaluate(({fault,KEY})=>{if(fault==='corrupt')localStorage.setItem(KEY,'{');if(fault==='write'){const native=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k===KEY)throw Error('denied');return native.call(this,k,v)}}if(fault==='locks'){const native=navigator.locks.request.bind(navigator.locks);navigator.locks.request=(name,...a)=>{if(name==='mla:musicbrainz:request:v1')throw Error('unavailable');return native(name,...a)}}},{fault,KEY});const r=await call(g.pages[0],base+`/api/ok?g=fault-${fault}`);assert(r.error);assert.equal((await measure(g)).fetchStarts.length,0);pass('fail closed: '+fault);await g.c.close();
  }
  // Real UI with synthetic archive only: traffic failures do not acquire save locks.
  for(const fault of ['corrupt','busy']){
   g=await group('archive-'+fault);await g.c.route('https://musicbrainz.org/**',r=>r.fulfill({json:{count:0,'release-groups':[]}}));
   const p=g.pages[0];await p.goto(base+'/');await p.evaluate(()=>MLAReady);
   await p.evaluate(({fault,KEY})=>{if(fault==='corrupt')localStorage.setItem(KEY,'{');else localStorage.setItem(KEY,JSON.stringify({version:1,lastStartAt:0,cooldownUntil:Date.now()+15000}))},{fault,KEY});
   await p.locator('[data-search-mode=title]').click();await p.locator('#query').fill('synthetic');await p.locator('#search-btn').click();
   await p.waitForFunction(fault=>document.querySelector('#status').textContent.includes(fault==='corrupt'?'coordination data':'Waiting'),fault);
   await p.locator('#ui-language').selectOption('ja');assert.match(await p.locator('#status').innerText(),fault==='corrupt'?/通信制御データ/:/通信開始/);
   await p.locator('#ui-language').selectOption('en');assert.match(await p.locator('#status').innerText(),fault==='corrupt'?/coordination data/:/Waiting/);
   await p.locator('#manual-add-trigger').click();await p.locator('#manual-title').fill('Synthetic during '+fault);await p.locator('#manual-artist').fill('Synthetic artist');
   const photo=await p.evaluate(()=>{const c=document.createElement('canvas');c.width=c.height=8;c.getContext('2d').fillRect(0,0,8,8);return c.toDataURL().split(',')[1]});
   await p.locator('#album-photo').setInputFiles({name:'synthetic.png',mimeType:'image/png',buffer:Buffer.from(photo,'base64')});await p.locator('#save').click();await p.waitForFunction(()=>!document.querySelector('#modal').classList.contains('open'));
   const snapshot=()=>p.evaluate(async()=>{const db=await new Promise((ok,no)=>{const r=indexedDB.open('mla-archive-v1');r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error)});try{return await new Promise((ok,no)=>{const tx=db.transaction('archive'),r=tx.objectStore('archive').get('current');tx.oncomplete=()=>ok(r.result);tx.onerror=()=>no(tx.error)})}finally{db.close()}});
   assert.equal((await snapshot()).listening[0].artist,'Synthetic artist');
   await p.waitForFunction(()=>[...document.querySelectorAll('#library img')].some(i=>i.complete&&i.naturalWidth>0));
   await p.locator('#insights-screen').click();assert(await p.locator('#insights-content').isVisible());await p.locator('#archive-screen').click();
   const download=p.waitForEvent('download');await p.locator('#export-json').click();const exported=JSON.parse(fs.readFileSync(await (await download).path(),'utf8'));assert.equal(exported.version,3);assert(exported.listening[0].photo.startsWith('data:image/'));
   await p.locator('#library button').filter({hasText:'Synthetic during '+fault}).click();await p.locator('#view-edit').click();await p.locator('#memo').fill('Edited while search unavailable');await p.locator('#save').click();await p.waitForFunction(()=>!document.querySelector('#modal').classList.contains('open'));assert.equal((await snapshot()).listening[0].memo,'Edited while search unavailable');
   await p.locator('#library button').filter({hasText:'Synthetic during '+fault}).click();await p.locator('#view-edit').click();await p.locator('#delete').click();await p.locator('#delete-accept').click();await p.waitForFunction(()=>!document.querySelector('#modal').classList.contains('open'));assert.equal((await snapshot()).listening.length,0);
   p.on('dialog',d=>d.accept());await p.locator('#import-json').setInputFiles({name:'synthetic.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(exported))});await p.waitForFunction(()=>!document.querySelector('#ui-language').disabled);assert.equal((await snapshot()).listening[0].artist,'Synthetic artist');await p.reload();await p.evaluate(()=>MLAReady);assert.equal((await snapshot()).listening[0].artist,'Synthetic artist');
   pass('archive CRUD/photos/Insights/JSON and JA/EN while search '+fault);await g.c.close();
  }
  pass('complete',{browser:browserName,version:browser.version()});
 }catch(e){console.error(e);process.exitCode=1;checks.push({failure:String(e),stack:e.stack})}
 finally{
  for(const c of contexts)await c.close().catch(()=>{});await browser?.close();server.closeAllConnections();cors.closeAllConnections();server.close();cors.close();
  fs.writeFileSync(process.argv[3]||`/tmp/mla-transport-${browserName}.json`,JSON.stringify({browser:browserName,checks,timing,received},null,2));
 }
})();

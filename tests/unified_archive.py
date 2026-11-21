"""Unified persistence acceptance: disposable origins/contexts, synthetic data only.
Run: python -u tests/unified_archive.py --browser chromium|webkit
Faults and private closure access are injected into intercepted test files only.
"""
import argparse, base64, copy, json, os, threading
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
from data_preservation import seed_data, PHOTO

ROOT=Path(__file__).resolve().parents[1]
KEYS=['my-music-archive-photos-v1','my-music-archive-pilot-v03','my-music-archive-pilot-v1','mma-ui-language','mma-ui-grid-display-v1']
SEAM="""window.probe={db:()=>db,save:saveDB,commit:commitDB,busy:()=>operationBusy||saving,failed:()=>loadFailed,conflict:()=>externalChanged,section:setSection,store:lifecycle,settings:()=>settingsQueue};"""
INJECT="""
window.fault=JSON.parse(sessionStorage.getItem('mla-test-fault')||'{}');window.checkpoints=[];
window.checkpoint=async name=>{checkpoints.push(name);if(fault.throwAt===name)throw Error('synthetic interruption '+name);if(fault.pauseAt===name)await new Promise(r=>window.resume=r)};
const add=IDBObjectStore.prototype.add,put=IDBObjectStore.prototype.put;
function faultWrite(store,value){if(store.transaction.db.name!=='mla-archive-v1')return;
 if(fault.quotaStore===store.name)throw new DOMException('synthetic quota','QuotaExceededError');
 if(fault.failReady&&store.name==='meta'&&value.status==='ready')throw Error('synthetic finalization failure');
 if(fault.abortStore===store.name)store.transaction.abort();
}
IDBObjectStore.prototype.add=function(value,...args){faultWrite(this,value);return add.call(this,value,...args)};
IDBObjectStore.prototype.put=function(value,...args){faultWrite(this,value);return put.call(this,value,...args)};
const get=IDBObjectStore.prototype.get;
IDBObjectStore.prototype.get=function(...args){if(fault.failRead&&this.transaction.db.name==='mla-archive-v1')throw Error('synthetic read error');return get.apply(this,args)};
"""
STATE="""async()=>{const r=await new Promise((ok,no)=>{const r=indexedDB.open('mla-archive-v1',1);r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error)});try{return await new Promise((ok,no)=>{const tx=r.transaction(['archive','photos','settings','meta'],'readonly'),out={};let n=4;for(const s of ['archive','photos','settings','meta']){out[s]=[];const q=tx.objectStore(s).openCursor();q.onsuccess=()=>{const c=q.result;if(c){out[s].push([c.key,c.value]);c.continue()}else if(!--n)ok(out)}}tx.onabort=()=>no(tx.error)})}finally{r.close()}}"""
class Quiet(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
 def log_message(self,*a):pass

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--browser',choices=['chromium','webkit'],default='chromium');args=parser.parse_args()
 server=ThreadingHTTPServer(('127.0.0.1',0),Quiet);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
 source=(ROOT/'index.html').read_text().replace("setSection('listening');showStorageState();",SEAM+"setSection('listening');showStorageState();")
 module=(ROOT/'archive-store.js').read_text()
 module=module.replace("   const meta={schema:1,status:'pending'", "   await checkpoint('prepared');\n   const meta={schema:1,status:'pending'")
 module=module.replace('ready=false;\n   const state=await read();','ready=false;\n   await checkpoint("published");\n   const state=await read();')
 module=module.replace("if(state.meta.status==='pending')await transaction", "await checkpoint('verified');\n   if(state.meta.status==='pending')await transaction")
 assert module.count('await checkpoint(')==3

 results=[]
 def passed(name):results.append(name);print('PASS',name,flush=True)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if args.browser=='chromium' else pw.webkit.launch()
  def fresh(seed=None,initial_fault=None):
   c=browser.new_context(accept_downloads=True);c.route('https://**/*',lambda r:r.abort());c.route(url+'/seed',lambda r:r.fulfill(body='<p>synthetic seed</p>',content_type='text/html'))
   c.route(url+'/',lambda r:r.fulfill(body=source,content_type='text/html'));c.route(url+'/archive-store.js',lambda r:r.fulfill(body=module,content_type='application/javascript'))
   c.add_init_script(INJECT)
   p=c.new_page();p.set_default_timeout(10000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)));answers=[];alerts=[]
   def dialog(d):
    if d.type=='prompt':
     a=answers.pop(0) if answers else None
     if a is None:d.dismiss()
     else:d.accept(str(a))
    elif d.type=='beforeunload':d.accept()
    elif d.type=='confirm' and answers and answers[0]=='cancel-confirm':answers.pop(0);d.dismiss()
    else:alerts.append(d.message);d.accept()
   p.on('dialog',dialog);p.goto(url+'/seed')
   if seed:p.evaluate('s=>{for(const [k,v] of Object.entries(s))localStorage.setItem(k,v)}',seed)
   if initial_fault:p.evaluate('(f)=>sessionStorage.setItem("mla-test-fault",JSON.stringify(f))',initial_fault)
   return c,p,answers,alerts,errors
  def ready(p):p.wait_for_function('window.probe&&!probe.busy()');p.evaluate('()=>MLAReady')
  def start(p):p.goto(url+'/');ready(p)
  def data(p):return p.evaluate('probe.db()')
  def state(p):return p.evaluate(STATE)
  def ls(p):return p.evaluate('()=>Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))')
  def save(p,d):return p.evaluate('(d)=>probe.save(d)',d)
  def exported(p,answers,index=None):
   if index is not None:answers.append(index)
   with p.expect_download() as dl:p.locator('#export-json').click()
   return Path(dl.value.path()).read_bytes()
  def imported(p,files):
   p.locator('#import-json').set_input_files([dict(name=f'branch{i}.json',mimeType='application/json',buffer=f) for i,f in enumerate(files)]);ready(p)
  original=seed_data();original['extra']={'preserve':['unknown',1]};original['listening'][0]['custom']={'nested':True}
  # New user and settings: no localStorage writes, real browser persistence.
  c,p,a,alerts,e=fresh();start(p);assert not p.evaluate('probe.failed()');assert save(p,original);assert ls(p)=={}
  p.reload();ready(p);assert data(p)==original
  p.locator('#ui-language').select_option('ja');p.evaluate('probe.settings()');p.reload();ready(p);assert p.locator('#ui-language').input_value()=='ja'
  assert ls(p)=={} and not e;passed('new user: records/photos/settings persist without localStorage writes');c.close()
  # Legacy v3, repeated migration and all archive images/Insights.
  pref={'listening':['rating','date'],'collection':['store'],'live':['artists','memo']}
  seed={KEYS[1]:json.dumps(original),KEYS[3]:'en',KEYS[4]:json.dumps(pref)}
  c,p,a,alerts,e=fresh(seed);start(p);before_ls=ls(p);assert data(p)==original
  first=state(p)
  for _ in range(3):p.reload();ready(p);assert state(p)==first and data(p)==original and ls(p)==before_ls
  assert first['settings'][0][1]['display']==pref
  for area in ['listening','collection','live']:
   p.locator(f'[data-section={area}]').click();p.wait_for_function("Array.from(document.querySelectorAll('#library img')).every(x=>x.complete&&x.naturalWidth>0)")
   p.locator('#insights-screen').click();assert p.locator('#'+area+'-insights').inner_text();p.locator('#archive-screen').click()
  portable=exported(p,a);assert json.loads(portable)==original
  with p.expect_download() as dl:p.locator('#export-csv').click()
  csv=Path(dl.value.path()).read_text(encoding='utf-8-sig');assert 'rating_5' in csv and 'listening' in csv and 'live' in csv
  imported(p,[portable]);p.reload();ready(p);assert data(p)==original and ls(p)==before_ls
  passed('v3 migration exact, repeated startup idempotent, original retained, JSON/CSV/Insights');c.close()
  # v1 array IDs must be stable across fresh independent migrations.
  v1=[{'id':'legacy','title':'','artist':'  ','rating':3,'listened':'2025-01-02','photo':PHOTO}]
  ids=[]
  for _ in range(2):
   c,p,a,alerts,e=fresh({KEYS[2]:json.dumps(v1)});start(p);d=data(p);assert d['listening'][0]['rating']=='6' and d['listening'][0]['date']=='2025-01-02';ids.append(d['listening'][0]['entryId']);assert ls(p)[KEYS[2]]==json.dumps(v1);c.close()
  assert ids[0]==ids[1];passed('v1 migration and deterministic IDs; historical score/date/blank fields preserved')
  # Current photo-ID archive is created using the actual previous storage module.
  c,p,a,alerts,e=fresh();p.add_script_tag(url=url+'/photo-store.js')
  packed=p.evaluate('(d)=>MLAPhotos.pack(d)',original);packed['legacyStamp']=p.evaluate('()=>MLAPhotos.idFor(JSON.stringify([null,null]))')
  p.evaluate('([k,d])=>localStorage.setItem(k,JSON.stringify(d))',[KEYS[0],packed]);start(p);assert data(p)==original
  oldphotos=p.evaluate("async()=>{const d=await new Promise(r=>{const q=indexedDB.open('mla-photos-v1');q.onsuccess=()=>r(q.result)});const values=await new Promise(r=>{const q=d.transaction('photos').objectStore('photos').getAll();q.onsuccess=()=>r(q.result)});d.close();return values}")
  assert set(oldphotos)=={r['photo'] for area in ['listening','collection','live'] for r in original[area]}
  assert json.loads(exported(p,a))==original;passed('current photo-ID archive and old IndexedDB preserved, photo bytes exact');c.close()
  # Atomic failures at all object stores: nothing, including new photos, is published.
  for store in ['archive','photos','settings','meta']:
   c,p,a,alerts,e=fresh(seed,{'quotaStore':store});start(p);assert p.evaluate('probe.failed()');assert ls(p)==seed
   assert all(not v for v in state(p).values());assert not save(p,original)
   c.close()
  passed('migration quota injection in all stores: atomic abort, no empty archive publication, original intact')

  for fault in [{'throwAt':'prepared'},{'abortStore':'archive'}]:
   c,p,a,alerts,e=fresh(seed,fault);start(p);assert p.evaluate('probe.failed()');assert all(not v for v in state(p).values()) and ls(p)==seed;c.close()
  c,p,a,alerts,e=fresh(seed,{'pauseAt':'prepared'});p.goto(url+'/',wait_until='commit');p.wait_for_function("checkpoints.includes('prepared')");assert all(not v for v in state(p).values());p.close()
  p=c.new_page();p.on('dialog',lambda d:d.accept());start(p);assert data(p)==original and ls(p)==seed;c.close()
  passed('pre-publication exception/page close and transaction abort preserve source; fresh retry exact')
  for settings in [{KEYS[3]:'invalid'},{KEYS[4]:'{'},{KEYS[4]:json.dumps({'live':['release']})}]:
   c,p,a,alerts,e=fresh({**seed,**settings});start(p);assert p.evaluate('probe.failed()');assert all(not v for v in state(p).values());assert ls(p)=={**seed,**settings};c.close()
  passed('malformed persistent settings stop migration without overwriting originals')

  # Migration committed but not finalized; reload verifies and resumes without copying again.
  for fault in [{'throwAt':'published'},{'throwAt':'verified'},{'failReady':True}]:
   c,p,a,alerts,e=fresh(seed,fault);start(p);assert p.evaluate('probe.failed()')
   pending=state(p);assert pending['meta'][0][1]['status']=='pending';assert not save(p,original) and ls(p)==seed
   # Remove fault for the next document while retaining the same browser context.
   p.evaluate("sessionStorage.removeItem('mla-test-fault')")
   p.reload();ready(p);assert not p.evaluate('probe.failed()') and data(p)==original
   assert state(p)['meta'][0][1]['status']=='ready';assert ls(p)==seed
   c.close()
  passed('published/verified/finalization exceptions: pending state blocks writes and safely resumes')
  # Close actual page at publication boundary, keeping persistent browser context.
  c,p,a,alerts,e=fresh(seed,{'pauseAt':'published'});p.goto(url+'/',wait_until='commit');p.wait_for_function("checkpoints.includes('published')")
  assert state(p)['meta'][0][1]['status']=='pending';p.close()
  p=c.new_page();p.on('dialog',lambda d:d.accept());start(p);assert data(p)==original and ls(p)==seed;c.close()
  passed('page termination after atomic migration publication: resume/reload exact')
  # Invalid/branched originals and missing photos fail closed, raw export remains available.
  for raw in ['{',json.dumps({'version':3,'listening':[]}),json.dumps({**packed,'legacyStamp':'wrong'}),json.dumps(packed)]:
   c,p,a,alerts,e=fresh({KEYS[0]:raw});start(p);assert p.evaluate('probe.failed()') and ls(p)=={KEYS[0]:raw}
   with p.expect_download() as dl:p.locator('#recover-source').click()
   recovery=json.loads(Path(dl.value.path()).read_text());assert recovery['legacy']['sources'][0]['raw']==raw
   assert not save(p,original);c.close()
  passed('corrupt/branched/missing-photo originals stop saving; raw recovery retains original')
  # Ordinary save quota abort and UI input retention, retry, all form CRUD/photo controls.
  c,p,a,alerts,e=fresh(seed);start(p)
  for area in ['listening','collection','live']:
   p.locator(f'[data-section={area}]').click()
   p.locator('#add-live-trigger' if area=='live' else '#manual-add-trigger').click()
   title='Synthetic '+area;p.locator('#live-title' if area=='live' else '#manual-title').fill(title)
   if area!='live':p.locator('#manual-artist').fill('Synthetic artist')
   def upload(selector,color):
    image=p.evaluate("color=>{const c=document.createElement('canvas');c.width=c.height=8;const x=c.getContext('2d');x.fillStyle=color;x.fillRect(0,0,8,8);return c.toDataURL()}",color)
    p.locator(selector).set_input_files(dict(name='synthetic.png',mimeType='image/png',buffer=base64.b64decode(image.split(',')[1])))
   upload('#live-photo' if area=='live' else '#album-photo','blue')
   before=state(p);p.evaluate("fault.quotaStore='archive'")
   p.locator('#live-form > button' if area=='live' else '#save').click();ready(p)
   assert state(p)==before and p.locator('#live-title' if area=='live' else '#manual-title').input_value()==title
   assert p.locator('#live-photo' if area=='live' else '#album-photo').evaluate('(e)=>e.files.length')==1
   p.evaluate('fault={}');p.locator('#save-return').click();p.locator('#live-form > button' if area=='live' else '#save').click();ready(p)
   created=next(r for r in data(p)[area] if r['title']==title);assert created['photo'].startswith('data:image/')
   def edit():

    p.locator('#library button').filter(has_text=title).first.click();p.locator('#view-edit').click()
   edit();p.locator('#memo').fill('edited');upload('#e-live-photo' if area=='live' else '#album-photo','red');p.locator('#save').click();ready(p)
   updated=next(r for r in data(p)[area] if r['title']==title);assert updated['memo']=='edited' and updated['photo']!=created['photo']
   edit();p.locator('#remove-photo' if area=='live' else '#remove-album-photo').click();ready(p);assert next(r for r in data(p)[area] if r['title']==title)['photo']==''
   p.locator('#close').click();edit();upload('#e-live-photo' if area=='live' else '#album-photo','blue');p.locator('#save').click();ready(p);assert next(r for r in data(p)[area] if r['title']==title)['photo'];edit();p.locator('#delete').click();p.locator('#delete-accept').click();ready(p);assert data(p)[area]==original[area]
  assert ls(p)==seed and not e;passed('all archives: failed save retains input/file; retry, create/edit/delete and photo replace/remove');c.close()
  # Photo failure keeps the existing explicit cancel / no-selected-photo choice.
  c,p,a,alerts,e=fresh(seed);start(p);p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Photo fallback');p.locator('#manual-artist').fill('Synthetic')
  upload('#album-photo','yellow');before=state(p);p.evaluate("fault.quotaStore='photos'");a.append('cancel-confirm');p.locator('#save').click();ready(p)
  assert state(p)==before and p.locator('#album-photo').evaluate('(e)=>e.files.length')==1
  p.locator('#save-return').click();p.locator('#save').click();ready(p)
  assert next(r for r in data(p)['listening'] if r['title']=='Photo fallback')['photo']==''
  passed('photo write failure: cancel preserves file and archive; explicit no-photo fallback saves record');c.close()
  # Lost BroadcastChannel notification: transaction generation prevents stale overwrite.
  c,p,a,alerts,e=fresh(seed);start(p);q=c.new_page();q.on('dialog',lambda d:d.accept());q.add_init_script('window.BroadcastChannel=undefined');q.goto(url+'/');ready(q)
  newer=copy.deepcopy(original);newer['live'][0]['memo']='tab one';assert save(p,newer)
  assert not save(q,original);assert data(p)==newer
  q.reload();ready(q);assert data(q)==newer
  # An actual previous-version tab uses the old module and the same lock.
  import subprocess
  old_source=subprocess.check_output(['git','show','fdbefae6:index.html'],cwd=ROOT,text=True).replace("setSection('listening');showStorageState();","window.oldBusy=()=>operationBusy||saving;setSection('listening');showStorageState();")
  c.route(url+'/legacy',lambda r:r.fulfill(body=old_source,content_type='text/html'))
  old=c.new_page();old.on('dialog',lambda d:d.accept());old.goto(url+'/legacy');old.evaluate('()=>MLAReady');old.wait_for_function('window.oldBusy&&!oldBusy()')
  branched=copy.deepcopy(original);branched['live'][0]['memo']='old tab branch'
  old.locator('#import-json').set_input_files(dict(name='old.json',mimeType='application/json',buffer=json.dumps(branched).encode()));old.wait_for_function('(k)=>JSON.parse(localStorage.getItem(k)||"null")?.live?.[0]?.memo==="old tab branch"',arg=KEYS[0])
  p.wait_for_function('probe.conflict()');frozen=state(p);assert not save(p,original) and state(p)==frozen
  p.reload();ready(p);assert p.evaluate('probe.failed()')
  newfile=exported(p,a,0);oldfile=exported(p,a,1);legacyfile=exported(p,a,2)
  assert json.loads(newfile)==newer and json.loads(oldfile)==branched and json.loads(legacyfile)==original
  # Existing requirement: every current branch must be exported and read back.
  a.append('1');imported(p,[newfile]);assert state(p)==frozen
  a.append('1');imported(p,[newfile,oldfile,legacyfile]);assert data(p)==newer
  assert ls(p)[KEYS[1]]==seed[KEYS[1]]
  passed('lost notifications prevent stale write; real old-version tab branches; all-branch verified recovery');c.close()
  # Save pause, same-lock contention, uncooperative old update, read failures and damage.
  c,p,a,alerts,e=fresh(seed);start(p);before=state(p)
  p.evaluate("fault.pauseAt='verified';void(window.savingResult=probe.save({...probe.db(),live:[]}))")
  p.wait_for_function("typeof resume==='function'")
  q=c.new_page();q.on('dialog',lambda d:d.accept());q.goto(url+'/');ready(q);assert q.evaluate('probe.failed()')
  p.evaluate('resume()');assert p.evaluate('()=>savingResult');p.reload();ready(p)
  # Legacy update after publication must leave pending and stop, never finalize over it.
  p.evaluate("fault.pauseAt='published';void(window.savingResult=probe.save({...probe.db(),live:[]}))");p.wait_for_function("typeof resume==='function'")
  q.evaluate('([k,v])=>localStorage.setItem(k,v)',[KEYS[1],json.dumps(branched)])
  p.evaluate('resume()');assert not p.evaluate('()=>savingResult');assert state(p)['meta'][0][1]['status']=='pending'
  p.reload();ready(p);assert p.evaluate('probe.failed()')
  pending_file=exported(p,a,0);branch_file=exported(p,a,2);a.append('1');imported(p,[pending_file,branch_file]);assert not p.evaluate('probe.failed()') and state(p)['meta'][0][1]['status']=='ready'
  c.close()
  passed('save pause/lock contention and legacy update during pending publication fail closed')
  c,p,a,alerts,e=fresh(seed);start(p);before=state(p);p.evaluate('fault.failRead=true');assert not save(p,original)
  p.evaluate('fault={}');assert state(p)==before;p.reload();ready(p)
  p.evaluate("async()=>{const d=await new Promise(r=>{const q=indexedDB.open('mla-archive-v1');q.onsuccess=()=>r(q.result)});await new Promise(r=>{const tx=d.transaction('photos','readwrite'),q=tx.objectStore('photos').openCursor();q.onsuccess=()=>{const c=q.result;if(c)c.update('corrupt')};tx.oncomplete=r});d.close()}")
  p.reload();ready(p);assert p.evaluate('probe.failed()') and not save(p,original);assert ls(p)==seed
  passed('read exceptions and photo corruption cannot become empty data or overwrite original');c.close()
  # A normal save interrupted AFTER commit retains the most recent verified original.
  c,p,a,alerts,e=fresh(seed);start(p);previous=data(p);p.evaluate("fault.throwAt='published'")
  changed=copy.deepcopy(previous);changed['live']=[];assert not save(p,changed) and p.evaluate('probe.failed()')
  snapshot=state(p);assert dict(snapshot['meta'])['current']['status']=='pending' and dict(snapshot['meta'])['previous']['status']=='ready'
  assert json.loads(exported(p,a,4))==previous
  with p.expect_download() as dl:p.locator('#recover-source').click()
  recovery=json.loads(Path(dl.value.path()).read_text());assert len(recovery['unified']['archive'])==2
  p.reload();ready(p);assert data(p)==changed and ls(p)==seed
  passed('post-commit ordinary-save interruption retains previous verified records/photos and resumes');c.close()
  # Unknown future schema refuses normal writes, while raw recovery stays version-agnostic.
  c,p,a,alerts,e=fresh(seed);start(p)
  p.evaluate("async()=>{await new Promise((ok,no)=>{const q=indexedDB.open('mla-archive-v1',2);q.onsuccess=()=>{q.result.close();ok()};q.onerror=()=>no(q.error)})}")
  p.reload();ready(p);assert p.evaluate('probe.failed()') and not save(p,original)
  with p.expect_download() as dl:p.locator('#recover-source').click()
  rescued=json.loads(Path(dl.value.path()).read_text());assert rescued['unified']['archive'] and rescued['unified']['photos'] and ls(p)==seed
  passed('unsupported DB version stops normal access; raw record/photo recovery remains available');c.close()
  # Record body exceeds usual localStorage quota; no limit simulation here.
  import time
  c,p,a,alerts,e=fresh();start(p)
  large={'version':3,'listening':[dict(entryId='large-'+str(i),title='Synthetic '+str(i),artist='Synthetic',memo='x'*6000,photo=PHOTO) for i in range(1200)],'collection':[],'live':[]}
  started=time.monotonic();assert save(p,large);saved_seconds=time.monotonic()-started
  p.reload();ready(p);assert data(p)==large and ls(p)=={}
  assert json.loads(exported(p,a))==large
  print('MEASURE',json.dumps({'records':1200,'portableBytes':len(json.dumps(large).encode()),'saveSeconds':round(saved_seconds,3),'browser':args.browser}),flush=True)
  passed('1200 synthetic records >7 MB: save/reload/portable JSON exact, no localStorage writes');c.close()
  browser.close()
 server.shutdown()
 print(json.dumps({'browser':args.browser,'passed':len(results),'cases':results},ensure_ascii=False),flush=True)

if __name__=='__main__':main()

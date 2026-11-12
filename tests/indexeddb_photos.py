"""Isolated Chromium, synthetic data only. python -u tests/indexeddb_photos.py"""
import base64, copy, json, os, threading, subprocess
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, QuietHandler
from data_preservation import seed_data, PHOTO
LEGACY='my-music-archive-pilot-v03'
KEY='my-music-archive-photos-v1'
SEAM="""window.probe={db:()=>db,save:saveDB,commit:commitDB,edit:openEdit,section:setSection,busy:()=>operationBusy,failed:()=>loadFailed};"""
INJECT="""
window.failPhoto=sessionStorage.getItem('failPhoto')==='yes';window.failRef=sessionStorage.getItem('failRef')==='yes';
const get=IDBObjectStore.prototype.get;
IDBObjectStore.prototype.get=function(...args){const r=get.apply(this,args);if(window.mismatch&&args[0]===window.mismatchId){window.mismatch=false;r.addEventListener('success',()=>Object.defineProperty(r,'result',{value:'synthetic read mismatch'}))}return r};
const add=IDBObjectStore.prototype.add;
IDBObjectStore.prototype.add=function(...args){
 if(window.failPhoto)throw new DOMException('synthetic quota','QuotaExceededError');
 return add.apply(this,args);
};
const set=Storage.prototype.setItem;
Storage.prototype.setItem=function(k,v){if(window.failRef&&k==='my-music-archive-photos-v1')throw new DOMException('synthetic quota','QuotaExceededError');return set.call(this,k,v)};
"""

def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 url=f'http://127.0.0.1:{server.server_port}'
 source=(ROOT/'index.html').read_text().replace('<script>\nglobalThis.MLAReady=', '''<script>
if(sessionStorage.getItem('pauseCopy')==='yes'){const pack=MLAPhotos.pack;window.MLAPhotos={...MLAPhotos,pack:async d=>{const result=await pack(d);await new Promise(r=>window.resumeCopy=r);return result}}}
globalThis.MLAReady=''' ).replace("setSection('listening');showStorageState();",SEAM+"setSection('listening');showStorageState();")
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
  ctx=browser.new_context(accept_downloads=True)
  ctx.route(url+'/',lambda r:r.fulfill(body=source,content_type='text/html'))
  old_source=subprocess.check_output(['git','show','c2c719d:index.html'],cwd=ROOT).decode()
  ctx.route(url+'/rollback',lambda r:r.fulfill(body=old_source,content_type='text/html'))
  ctx.route('https://**/*',lambda r:r.abort())
  ctx.add_init_script(INJECT)
  accept_dialog=lambda d:d.accept()
  dismiss_dialog=lambda d:d.dismiss()
  p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',accept_dialog)
  p.goto(url);p.wait_for_function('window.probe')
  def raw():return p.evaluate('(k)=>localStorage.getItem(k)',KEY)
  def ready():p.wait_for_function('window.probe && !probe.busy()')
  def seed(data):
   p.evaluate('([k,l,d])=>{localStorage.removeItem(k);localStorage.setItem(l,JSON.stringify(d))}',[KEY,LEGACY,data]);p.reload();ready()
  original=seed_data();seed(original)
  assert p.evaluate('probe.db()')==original
  packed=json.loads(raw());assert all('photoId' in r and 'photo' not in r for a in ['listening','collection','live'] for r in packed[a])
  assert p.evaluate('(k)=>JSON.parse(localStorage.getItem(k))',LEGACY)==original
  for area in ['listening','collection','live']:
   p.evaluate('(a)=>probe.section(a)',area)
   assert p.locator('#library img').first.evaluate('(e)=>e.complete && e.naturalWidth>0')
  print('PASS migration: all fields/photos equal, original retained, three areas display')
  with p.expect_download() as dl:p.locator('#export-json').click()
  portable=json.loads(Path(dl.value.path()).read_text());assert portable==original
  changed=copy.deepcopy(original);changed['live'][0]['photo']='';changed['listening'][0]['memo']='changed'
  assert p.evaluate('(d)=>probe.save(d)',changed)
  p.locator('#import-json').set_input_files(dict(name='legacy.json',mimeType='application/json',buffer=json.dumps(portable).encode()));ready()
  assert p.evaluate('probe.db()')==original
  print('PASS old JSON import and new portable JSON round trip')
  # New bytes for each test; no image decoding required in storage tests.
  other='data:image/svg+xml;base64,'+base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg" width="2" height="2"><rect width="2" height="2" fill="red"/></svg>').decode()
  replacement=copy.deepcopy(original);replacement['collection'][0]['photo']=other
  before=raw();p.evaluate('async v=>{window.mismatchId=await MLAPhotos.idFor(v);window.mismatch=true}',other)
  assert not p.evaluate('(d)=>probe.save(d,{kind:"restore"})',replacement)
  assert raw()==before and p.evaluate('probe.db()')==original
  print('PASS readback mismatch rejects publication without changing original')
  p.evaluate('failPhoto=true')
  assert not p.evaluate('(d)=>probe.save(d,{kind:"restore"})',replacement)
  assert raw()==before and p.evaluate('probe.db()')==original
  p.evaluate('failPhoto=false')
  assert p.evaluate('(d)=>probe.save(d,{kind:"restore"})',replacement)
  assert p.evaluate('probe.db()')==replacement
  print('PASS injected quota on restore preserves archive/photos; retry succeeds')
  # Reference publication fails after photo copy: reload/retry reuses immutable copy.
  p.evaluate('failRef=true');before=raw()
  assert not p.evaluate('(d)=>probe.save(d)',original);assert raw()==before
  p.reload();ready();assert p.evaluate('probe.db()')==replacement
  assert p.evaluate('(d)=>probe.save(d)',original)
  for area in ['listening','collection','live']:
   updated=copy.deepcopy(original);updated[area][0]['photo']=other
   assert p.evaluate('(d)=>probe.save(d)',updated)
   updated[area][0]['photo']=''
   assert p.evaluate('(d)=>probe.save(d)',updated)
   updated[area]=updated[area][1:]
   assert p.evaluate('(d)=>probe.save(d)',updated)
  print('PASS reference write failure + reload retry; replace/remove/delete in all areas')
  assert p.evaluate('(d)=>probe.save(d)',original)
  # Pause after copies, race an uncooperative tab, and verify final source check.
  p.evaluate("""()=>{const pack=MLAPhotos.pack;window.MLAPhotos={...MLAPhotos,pack:async d=>{const result=await pack(d);await new Promise(r=>window.resumeCopy=r);return result}};window.pending=probe.save({...probe.db(),live:[]})}""")
  
  try:p.wait_for_function('!!window.resumeCopy',timeout=5000)
  except Exception:
   print('DEBUG',p.evaluate('async()=>({result:await pending,body:document.body.innerText.slice(-4000)})'));raise
  q=ctx.new_page();q.goto(url);q.wait_for_function('window.probe')
  q.evaluate('(k)=>{const d=JSON.parse(localStorage.getItem(k));d.live[0].memo="other tab";localStorage.setItem(k,JSON.stringify(d))}',KEY)
  current=raw();p.evaluate('resumeCopy()');assert not p.evaluate('pending');assert raw()==current
  p.reload();ready();assert p.evaluate('probe.db().live[0].memo')=='other tab'
  # Legacy tab after migration; stamp must detect divergence even after reload.
  q.evaluate('(k)=>{const d=JSON.parse(localStorage.getItem(k));d.live[0].memo="old tab";localStorage.setItem(k,JSON.stringify(d))}',LEGACY)
  p.reload();ready();assert not p.evaluate('probe.save(probe.db())');assert raw()==current
  print('PASS tab race after copy, legacy divergence detected across reloads')
  q.close();seed(original)
  # UI photo failure: cancel retains exact input/file; retry with explicit no-photo choice.
  p.evaluate('probe.section("live")')
  p.locator('#add-live-trigger').evaluate('e=>e.click()')
  p.locator('#live-title').fill('Synthetic failed photo')
  p.locator('#live-notes').fill('keep this input')
  p.locator('#live-photo').set_input_files(dict(name='synthetic.png',mimeType='image/png',buffer=base64.b64decode(PHOTO.split(',')[1])))
  p.evaluate('failPhoto=true')
  p.remove_listener('dialog',accept_dialog);p.on('dialog',dismiss_dialog)
  p.locator('#live-form').evaluate('e=>e.requestSubmit()');ready()
  assert p.locator('#live-title').input_value()=='Synthetic failed photo'
  assert p.locator('#live-photo').evaluate('e=>e.files.length')==1
  # Original archive and selected file survive the declined fallback.
  assert len(p.evaluate('probe.db().live'))==2
  p.remove_listener('dialog',dismiss_dialog);p.on('dialog',accept_dialog)
  p.locator('#live-form').evaluate('e=>e.requestSubmit()');ready()
  assert p.evaluate('probe.db().live[0].title')=='Synthetic failed photo'
  assert p.evaluate('probe.db().live[0].photo')==''
  assert p.evaluate('probe.db().live[0].memo')=='keep this input'
  print('PASS new photo quota UI: cancel retains input/file; chosen no-photo save')
  p.evaluate('failPhoto=false')
  # Interrupt startup migration after copy, before publishing references.
  p.evaluate('([k,l,d])=>{localStorage.removeItem(k);localStorage.setItem(l,JSON.stringify(d));sessionStorage.setItem("pauseCopy","yes")}',[KEY,LEGACY,original])
  p.reload();p.wait_for_function('!!window.resumeCopy')
  assert raw() is None
  assert p.evaluate('(k)=>JSON.parse(localStorage.getItem(k))',LEGACY)==original
  p.close()
  p=ctx.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',accept_dialog);p.goto(url);ready()
  assert p.evaluate('probe.db()')==original
  # Fail migration reference publication, then reload to retry.
  p.evaluate('(k)=>{localStorage.removeItem(k);sessionStorage.setItem("failRef","yes")}',KEY)
  p.reload();ready();assert p.evaluate('probe.failed()');assert raw() is None
  p.evaluate('sessionStorage.removeItem("failRef")');p.reload();ready()
  assert p.evaluate('probe.db()')==original and raw() is not None
  print('PASS migration interruption by page close and failed publication + retry')
  # Confirm portable export really restores into the baseline main application.
  newest=copy.deepcopy(original);newest['collection'][0]['photo']=other;newest['live'][0]['memo']='prototype change'
  assert p.evaluate('(d)=>probe.save(d)',newest)
  with p.expect_download() as dl:p.locator('#export-json').click()
  rollback_json=Path(dl.value.path()).read_bytes()
  old=ctx.new_page();old.on('pageerror',lambda e:errors.append(str(e)));old.on('dialog',accept_dialog);old.goto(url+'/rollback')
  old.locator('#import-json').set_input_files(dict(name='portable.json',mimeType='application/json',buffer=rollback_json))
  old.wait_for_function('(k)=>JSON.parse(localStorage.getItem(k)).live[0].memo==="prototype change"',arg=LEGACY)
  assert old.evaluate('(k)=>JSON.parse(localStorage.getItem(k))',LEGACY)==newest
  old.close();seed(original)
  print('PASS rollback: actual baseline main restores new photo-inclusive JSON')
  # Missing bytes must stop export, and startup must never turn that into an empty DB.
  p.evaluate("""async()=>{await new Promise((resolve,reject)=>{const r=indexedDB.open('mla-photos-v1',1);r.onsuccess=()=>{const db=r.result,t=db.transaction('photos','readwrite');t.objectStore('photos').clear();t.oncomplete=()=>{db.close();resolve()}}})}""")
  notices=[]
  p.on('dialog',lambda d:notices.append(d.message))
  before=raw();p.locator('#export-json').click();p.wait_for_timeout(150)
  assert any('missing' in n for n in notices)
  p.reload();ready();assert p.evaluate('probe.failed()');assert raw()==before
  print('PASS missing photo export notification and fail-closed startup')
  assert not errors,errors
  browser.close()
 server.shutdown()
 print('PASS all synthetic IndexedDB prototype checks')
if __name__=='__main__':main()

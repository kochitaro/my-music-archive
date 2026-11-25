"""Isolated synthetic restore safety regression and capacity measurements.
Run: python3 tests/restore_safety.py
Set MLA_TEST_OUTPUT to retain JSON snapshots/screenshots outside the source tree.
The first 23 results repeat the original audit with explicit new acceptance criteria.
"""
import sys,json,copy,threading,hashlib,functools
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).parent))
from unified_archive import STATE,SEAM,INJECT
from data_preservation import seed_data
from playwright.sync_api import sync_playwright
import os,time
OUT=Path(os.environ.get('MLA_TEST_OUTPUT','/tmp/mla-restore-safety-results'));OUT.mkdir(parents=True,exist_ok=True); ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
html=(ROOT/'index.html').read_text().replace("setSection('listening');showStorageState();",SEAM.replace("section:setSection,","forceStopped:()=>{loadFailed=true;showStorageState()},section:setSection,")+"setSection('listening');showStorageState();")
module=(ROOT/'archive-store.js').read_text().replace("   const meta={schema:1,status:'pending'","   await checkpoint('prepared');\n   const meta={schema:1,status:'pending'").replace('ready=false;\n   const state=await read();','ready=false;\n   await checkpoint("published");\n   const state=await read();').replace("if(state.meta.status==='pending')await transaction","await checkpoint('verified');\n   if(state.meta.status==='pending')await transaction")
# Fail the second actual photo add, after the first request has been queued.
extra="""const origPut=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(...a){if(fault.finalization&&this.name==='meta'&&a[1]==='current'&&a[0]?.status==='ready')throw Error('synthetic finalization failed');if(fault.writeError&&this.name==='archive'&&this.transaction.db.name==='mla-archive-v1')throw new DOMException('synthetic write failure','UnknownError');return origPut.apply(this,a)};const origAdd=IDBObjectStore.prototype.add;window.photoAdds=0;IDBObjectStore.prototype.add=function(...a){if(fault.writeError&&this.name==='archive'&&this.transaction.mode==='readwrite')throw new DOMException('synthetic IDB write failed','UnknownError');if(this.name==='photos'&&this.transaction.db.name==='mla-archive-v1'&&fault.secondPhoto&&++photoAdds===2)throw new DOMException('second synthetic photo failed','UnknownError');return origAdd.apply(this,a)};"""
postonly='--post-only' in sys.argv
results=[r for r in json.loads((OUT/'results.json').read_text()) if not r['name'].startswith('restore-postcommit')] if postonly else []
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 print('BROWSER',browser.version,flush=True)
 def ready(p):p.evaluate('()=>MLAReady');p.wait_for_function('window.probe&&!probe.busy()')
 def fresh():
  c=browser.new_context(locale='en-US',accept_downloads=True);c.route('https://**/*',lambda r:r.abort());c.route(base+'/',lambda r:r.fulfill(body=html,content_type='text/html'));c.route(base+'/archive-store.js',lambda r:r.fulfill(body=module,content_type='application/javascript'));c.add_init_script(INJECT+extra)
  p=c.new_page();p.set_default_timeout(12000);alerts=[];p.on('dialog',lambda d:(alerts.append(d.message),d.accept()));p.goto(base);ready(p)
  original=seed_data();original['unknown']={'test':[True,None,'日本語']}
  # Three distinct real canvas images, ensuring byte/link comparisons are meaningful.
  images=p.evaluate("()=>['red','green','blue'].map(color=>{const c=document.createElement('canvas');c.width=c.height=3;c.getContext('2d').fillStyle=color;c.getContext('2d').fillRect(0,0,3,3);return c.toDataURL()})")
  for a,image in zip(['listening','collection','live'],images):
   for row in original[a]:row['photo']=image
  assert p.evaluate('(d)=>probe.save(d)',original)
  p.locator('#ui-language').select_option('ja');p.evaluate('probe.settings()');p.reload();ready(p)
  global newphotos
  newphotos=p.evaluate("()=>['yellow','purple'].map(color=>{const c=document.createElement('canvas');c.width=c.height=5;const x=c.getContext('2d');x.fillStyle=color;x.fillRect(0,0,5,5);return c.toDataURL()})")
  return c,p,original,alerts
 def snap(p):return p.evaluate(STATE)
 def export(p,index=None):
  if index is not None:
   p.once('dialog',lambda d:None) # prompt handled separately below
  with p.expect_download() as dl:p.locator('#export-json').click()
  return json.loads(Path(dl.value.path()).read_text())
 def check_images(p):
  for area in ['listening','collection','live']:
   p.locator(f'[data-section={area}]').click();p.wait_for_function("[...document.querySelectorAll('#library img')].every(x=>x.complete&&x.naturalWidth>0)")
 def record(name,**kw):
  item=dict(name=name,**kw);results[:]=[r for r in results if r['name']!=name];results.append(item);(OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(item,ensure_ascii=False),flush=True)
 def preserved(name,c,p,original,before,alerts):
  after=snap(p);mem=p.evaluate('probe.db()');photoAdds=p.evaluate('photoAdds');p.evaluate('fault={}');p.reload();ready(p);loaded=p.evaluate('probe.db()');after_reload=snap(p);portable=export(p);check_images(p)
  exact=before==after==after_reload and mem==loaded==portable==original
  (OUT/'snapshots').mkdir(exist_ok=True);(OUT/'snapshots'/(name.replace('/','-')+'.json')).write_text(json.dumps(dict(before=before,after=after,afterReload=after_reload,original=original,memory=mem,loaded=loaded,export=portable),ensure_ascii=False,indent=2));record(name,photoAdds=photoAdds,status='PASS' if exact else 'FAIL',beforeHash=digest(before),afterHash=digest(after),reloadHash=digest(after_reload),memoryExact=mem==original,loadedExact=loaded==original,backupExact=portable==original,counts={a:len(loaded[a]) for a in ['listening','collection','live']},alerts=alerts[-2:])
  c.close()
 for area in ([] if postonly else ['listening','collection','live']):
  for name,fault in [('write-error',{'writeError':True}),('transaction-abort',{'abortStore':'archive'}),('quota',{'quotaStore':'archive'}),('photo-partial',{'secondPhoto':True})]:
   c,p,original,alerts=fresh();before=snap(p);changed=copy.deepcopy(original);changed[area][0]['memo']='must not publish'
   # Two new data:image values force two photo insertions in the same transaction.
   changed[area][0]['photo']=newphotos[0];changed[area][1]['photo']=newphotos[1]
   p.evaluate('(f)=>fault=f',fault);ok=p.evaluate('(d)=>probe.save(d)',changed);assert ok is False
   preserved(area+'/'+name,c,p,original,before,alerts)
 # Actual JSON input handler/file parsing and restore persistence boundary.
 cases=[('invalid-json','{',{}),('missing-area',json.dumps({'version':3,'listening':[],'collection':[]}),{}),('unsupported-format',json.dumps({'version':99,'listening':[],'collection':[],'live':[]}),{}),('missing-required',None,{}),('photoId-without-bytes',None,{}),('restore-quota',None,{'quotaStore':'archive'}),('restore-photo-partial',None,{'secondPhoto':True})]
 for name,raw,fault in ([] if postonly else cases):
  c,p,original,alerts=fresh();before=snap(p);changed=copy.deepcopy(original);changed['live'][0]['memo']='restore replacement'
  if name=='missing-required':del changed['listening'][0]['title']
  if name=='photoId-without-bytes':changed['live'][0]['photoId']='sha256-missing';del changed['live'][0]['photo']
  if name=='restore-photo-partial':changed['live'][0]['photo']=newphotos[0];changed['live'][1]['photo']=newphotos[1]
  p.evaluate('(f)=>fault=f',fault)
  p.locator('#import-json').set_input_files(dict(name='synthetic.json',mimeType='application/json',buffer=(raw if raw is not None else json.dumps(changed)).encode()));ready(p)
  preserved(name,c,p,original,before,alerts)
 # A syntactically valid image data URL that cannot be decoded.
 c,p,original,alerts=fresh();before=snap(p);changed=copy.deepcopy(original);changed['listening'][0]['photo']='data:image/png;base64,NOT_AN_IMAGE'
 p.locator('#import-json').set_input_files(dict(name='bad-photo.json',mimeType='application/json',buffer=json.dumps(changed).encode()));ready(p)
 assert p.locator('#save-notice-reason').is_visible();assert 'listening' in p.locator('#save-notice-reason').inner_text()
 preserved('undecodable-photo',c,p,original,before,alerts)
 # Error after atomic publication: capture current and previous rather than assuming rollback.
 for point in ['published','verified','finalization']:
  c,p,original,alerts=fresh();before=snap(p);changed=copy.deepcopy(original);changed['live']=[];p.evaluate('(v)=>fault=v',{'finalization':True} if point=='finalization' else {'throwAt':point})
  p.locator('#import-json').set_input_files(dict(name='postcommit.json',mimeType='application/json',buffer=json.dumps(changed).encode()));ready(p);s=snap(p)
  assert p.locator('#save-notice-title').inner_text()=='復元結果の確認が必要です'
  assert '保存されました' in p.locator('#save-notice-info').inner_text()
  p.locator('#restore-recovery-title').click()
  with p.expect_download() as dl:p.locator('#export-before-restore').click()
  assert json.loads(Path(dl.value.path()).read_text())==original
  p.reload();ready(p);loaded=p.evaluate('probe.db()');s2=snap(p)
  # Both states carry packed photo IDs; prior archive and settings must be exact and all photo bytes retained.
  (OUT/'snapshots'/('postcommit-'+point+'.json')).write_text(json.dumps(dict(before=before,after=s,afterReload=s2,original=original,loaded=loaded),ensure_ascii=False,indent=2))
  previousPortable=p.evaluate('()=>probe.store.exportBranch(4)');assert previousPortable==original
  retained=dict(s['archive'])['previous']==dict(before['archive'])['current'] and dict(s['settings'])['previous']==dict(before['settings'])['current'] and s['photos']==before['photos']
  record('restore-postcommit-'+point,status='PASS' if loaded==changed and retained else 'FAIL',previousExact=retained,previousPortableExact=previousPortable==original,currentAfterReloadIsIncoming=loaded==changed,oldCounts={a:len(original[a]) for a in ['listening','collection','live']},reloadCounts={a:len(loaded[a]) for a in ['listening','collection','live']},currentStatus=dict(s['meta'])['current']['status'],reloadStatus=dict(s2['meta'])['current']['status'],alerts=alerts[-2:]);c.close()
 # Persistent recovery through settings, actual UI CRUD, and a second restore.
 c,p,original,alerts=fresh();incoming=copy.deepcopy(original);incoming['live']=[]
 def restore(value):
  p.locator('#import-json').set_input_files(dict(name='synthetic.json',mimeType='application/json',buffer=json.dumps(value).encode()));ready(p)
 def recovery():
  p.locator('#restore-recovery').evaluate('(e)=>e.open=true')
  with p.expect_download() as dl:p.locator('#export-before-restore').click()
  return json.loads(Path(dl.value.path()).read_text())
 restore(incoming);p.reload();ready(p);assert recovery()==original
 beforeSettings=snap(p);p.locator('#ui-language').select_option('en');p.evaluate('probe.settings()');p.reload();ready(p);assert recovery()==original
 p.locator('[data-section=listening]').click();p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Added after restore');p.locator('#manual-artist').fill('Synthetic');p.locator('#save').click();ready(p)
 p.locator('#library .coverbtn').filter(has_text='Added after restore').click();p.locator('#view-edit').click();p.locator('#memo').fill('Edited after restore');p.locator('#save').click();ready(p)
 p.reload();ready(p);assert recovery()==original
 after=snap(p);assert dict(after['archive'])['previous']==dict(beforeSettings['archive'])['previous'];assert len(after['archive'])==2
 assert after['photos']==beforeSettings['photos']
 record('pinned-recovery-settings-create-edit-reload',status='PASS',archiveSlots=len(after['archive']),photoCount=len(after['photos']),packedArchiveBytes=len(json.dumps(after['archive']).encode()),photoStringBytes=sum(len(v.encode()) for k,v in after['photos']))
 current=p.evaluate('probe.db()');restore(original);p.reload();ready(p);assert export(p)==original and recovery()==current
 record('recovered-json-restores-and-next-restore-replaces-recovery',status='PASS');c.close()
 # Old array JSON remains accepted, including real PNG and no-photo variants.
 c,p,original,alerts=fresh();legacy=[dict(id='legacy',entryId='stable-old',title='Legacy',artist='Synthetic',photo=original['listening'][0]['photo'],rating=4),dict(id='empty',title='',artist='',photo=None)]
 restore(legacy);p.reload();ready(p);loaded=p.evaluate('probe.db()');assert loaded['listening'][0]['entryId']=='stable-old' and loaded['listening'][0]['rating']=='8';assert recovery()==original
 record('legacy-json',status='PASS');c.close()
 # Quota during restore must preserve BOTH current and the pinned recovery slot.
 for store in ['archive','photos','settings','meta']:
  c,p,original,alerts=fresh();restore({**original,'live':[]});before=snap(p);candidate=copy.deepcopy(original);candidate['listening'][0]['photo']=newphotos[0];candidate['listening'][1]['photo']=newphotos[1]
  p.evaluate('(s)=>fault={quotaStore:s}',store);restore(candidate);assert snap(p)==before
  p.reload();ready(p);assert recovery()==original
  record('pinned-recovery-quota-'+store,status='PASS',beforeHash=digest(before),afterHash=digest(snap(p)));c.close()
 # Invalid photos never publish in any area; data URL syntax alone is insufficient.
 for area in ['listening','collection','live']:
  for bad in ['data:image/png;base64,aGVsbG8=','data:image/png;base64,','https://example.invalid/photo.png']:
   c,p,original,alerts=fresh();before=snap(p);candidate=copy.deepcopy(original);candidate[area][0]['photo']=bad;restore(candidate);assert snap(p)==before
   assert area in p.locator('#save-notice-reason').inner_text();p.reload();ready(p);assert export(p)==original;c.close()
 record('invalid-image-content-all-areas',status='PASS')
 # Normal photo formats and optional fields keep their exact portable representation.
 c,p,original,alerts=fresh();candidate=copy.deepcopy(original)
 jpeg=p.evaluate("()=>{const c=document.createElement('canvas');c.width=c.height=4;return c.toDataURL('image/jpeg')}")
 candidate['listening'][0]['photo']=jpeg;candidate['listening'][1].pop('photo');candidate['collection'][0]['photo']=None;candidate['live'][0]['photo']=''
 restore(candidate);p.reload();ready(p);assert export(p)==candidate;assert recovery()==original
 for lang in ['ja','en']:
  p.locator('#ui-language').select_option(lang);p.evaluate('probe.settings()');assert recovery()==original
  p.set_viewport_size({'width':390,'height':844});assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
 c.close();record('jpeg-png-optional-fields-ja-en-mobile',status='PASS')
 # Stopped-state adoption must reject bad photos too, while branch export remains usable.
 c,p,original,alerts=fresh();before=snap(p);p.evaluate('probe.forceStopped()');p.evaluate("()=>{window.prompt=()=> '1'}")
 candidate=copy.deepcopy(original);candidate['live'][0]['photo']='data:image/png;base64,NOT_AN_IMAGE';restore(candidate)
 assert snap(p)==before and any('Photo could not be decoded' in a for a in alerts)
 c.close();record('stopped-restore-photo-preflight',status='PASS')
 # A settings interruption after restore is not misreported as another interrupted restore.
 c,p,original,alerts=fresh();restore({**original,'live':[]});p.evaluate('fault={finalization:true}')
 p.locator('#ui-language').select_option('en');p.evaluate('probe.settings()');p.reload();ready(p)
 assert p.locator('#restore-result').is_hidden() and recovery()==original
 for lang in ['ja','en']:
  p.locator('#ui-language').select_option(lang);p.evaluate('probe.settings()');assert recovery()==original
  p.locator('#restore-recovery').screenshot(path=str(OUT/('recovery-'+lang+'.png')))
 record('settings-interruption-is-not-a-restore-resume',status='PASS');c.close()
 # Simulate a decoder that never calls either callback: timeout must reject before publication.
 c,p,original,alerts=fresh();before=snap(p)
 p.evaluate("()=>{const timer=window.setTimeout;window.setTimeout=(f,ms,...args)=>timer(f,ms===15000?0:ms,...args);window.Image=class{removeAttribute(){}}}")
 restore(original);assert snap(p)==before and 'timed out' in p.locator('#save-notice-reason').inner_text()
 record('photo-decoder-timeout-preserves-existing-data',status='PASS');c.close()
 # Measure distinct decode vs duplicate image cost without rewriting the JSON image bytes.
 c,p,original,alerts=fresh()
 uniqueImages=p.evaluate("()=>Array.from({length:60},(_,n)=>{const c=document.createElement('canvas');c.width=c.height=128;const x=c.getContext('2d');x.fillStyle='hsl('+n*6+',60%,50%)';x.fillRect(0,0,128,128);return c.toDataURL()})")
 large={'version':3,'listening':[dict(entryId='large-'+str(i),title='Large '+str(i),artist='Synthetic',memo='x'*6000,photo=uniqueImages[i%60]) for i in range(1200)],'collection':[],'live':[]}
 started=time.monotonic();decodeMilliseconds=p.evaluate('async(d)=>{const t=performance.now();await MLAPhotos.validateRestore(d);return performance.now()-t}',large);decodeSeconds=time.monotonic()-started
 started=time.monotonic();restore(large);restoreSeconds=time.monotonic()-started
 p.reload();ready(p);assert export(p)==large and recovery()==original
 state=snap(p);record('large-json-performance',status='PASS',records=1200,uniquePhotos=60,portableBytes=len(json.dumps(large).encode()),decodeSeconds=round(decodeSeconds,3),decodeInPageMilliseconds=round(decodeMilliseconds,1),restoreSeconds=round(restoreSeconds,3),archiveSlots=len(state['archive']),photoCount=len(state['photos']),packedArchiveBytes=len(json.dumps(state['archive']).encode()),photoStringBytes=sum(len(v.encode()) for k,v in state['photos']))
 # Retaining a large pre-restore archive must not add a third slot or drop it under quota.
 restore(original);p.reload();ready(p);assert recovery()==large
 p.locator('#ui-language').select_option('en');p.evaluate('probe.settings()');p.reload();ready(p);assert recovery()==large
 retained=snap(p);p.evaluate("fault.quotaStore='archive'");restore({**original,'live':[]});assert snap(p)==retained
 p.reload();ready(p);assert recovery()==large
 estimate=p.evaluate('()=>navigator.storage.estimate()')
 record('large-pre-restore-retention-and-quota',status='PASS',archiveSlots=len(retained['archive']),pinnedArchiveBytes=len(json.dumps(dict(retained['archive'])['previous']).encode()),photoCount=len(retained['photos']),browserStorageEstimate=estimate)
 c.close()
 assert len(results)==37 and all(r['status']=='PASS' for r in results),results
 browser.close()
server.shutdown()

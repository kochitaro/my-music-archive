"""Next-stage prototype: isolated real Chromium/IDB, synthetic pictures, injected quotas.
Run: python -u tests/indexeddb_recovery.py
"""
import copy, json, os, subprocess, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from ui_v0322 import ROOT, QuietHandler
from data_preservation import seed_data
KEY='my-music-archive-photos-v1'
LEGACY='my-music-archive-pilot-v03'
OLD='my-music-archive-pilot-v1'
SEAM='window.review={db:()=>db,save:saveDB,busy:()=>operationBusy,conflict:()=>externalChanged,failed:()=>loadFailed,section:setSection};'
INJECT="""
window.cap=Number(sessionStorage.getItem('cap'))||Infinity;
const set=Storage.prototype.setItem,remove=Storage.prototype.removeItem,put=IDBObjectStore.prototype.put,add=IDBObjectStore.prototype.add;
IDBObjectStore.prototype.add=function(...a){if(window.failPhoto&&this.transaction.db.name==='mla-photos-v1')throw new DOMException('synthetic photo quota','QuotaExceededError');return add.apply(this,a)};
Storage.prototype.setItem=function(k,v){if(this===localStorage){let total=k.length+String(v).length;for(let i=0;i<this.length;i++){const x=this.key(i);if(x!==k)total+=x.length+this.getItem(x).length}if(total>window.cap||window.failRef&&k==='my-music-archive-photos-v1')throw new DOMException('synthetic quota','QuotaExceededError')}return set.call(this,k,v)};
Storage.prototype.removeItem=function(k){const result=remove.call(this,k);if(window.interruptRemove&&k==='my-music-archive-pilot-v03'){window.interruptRemove=false;throw Error('synthetic interruption after deletion')}return result};
IDBObjectStore.prototype.put=function(...a){if(window.failJournal&&this.transaction.db.name==='mla-photo-maintenance-v1')throw Error('synthetic journal failure');return put.apply(this,a)};
"""

def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
 url=f'http://127.0.0.1:{server.server_port}'
 source=(ROOT/'index.html').read_text().replace("setSection('listening');showStorageState();",SEAM+"setSection('listening');showStorageState();")
 engine=(ROOT/'photo-lifecycle.js').read_text().replace("    if(stable(candidate)!==stable(verified))", "    if(window.pauseRecovery)await new Promise(r=>window.resumeRecovery=r);\n    if(stable(candidate)!==stable(verified))").replace('   check(snapshot); // Journal write awaited:', '   if(window.pauseCleanup)await new Promise(r=>window.resumeCleanup=r);\n   check(snapshot); // Journal write awaited:')
 old_source=subprocess.check_output(['git','show','c2c719d:index.html'],cwd=ROOT).decode()
 evidence=ROOT/'docs/indexeddb-recovery-evidence';evidence.mkdir(exist_ok=True)
 measurements=[];errors=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
  def context():
   ctx=browser.new_context(accept_downloads=True,locale='ja-JP')
   ctx.route(url+'/',lambda r:r.fulfill(body=source,content_type='text/html'))
   ctx.route(url+'/photo-lifecycle.js',lambda r:r.fulfill(body=engine,content_type='application/javascript'))
   ctx.route(url+'/legacy',lambda r:r.fulfill(body=old_source,content_type='text/html'))
   ctx.route('https://**/*',lambda r:r.abort());ctx.add_init_script(INJECT);return ctx
  def page(ctx,path=''):
   p=ctx.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept());p.goto(url+path);return p
  def ready(p):p.wait_for_function('window.review && !review.busy()')
  def raw(p,k=KEY):return p.evaluate('(k)=>localStorage.getItem(k)',k)
  def state(p):return [raw(p,k) for k in [KEY,LEGACY,OLD]]
  def use(p,selector,data,name='synthetic.json'):
   p.locator(selector).set_input_files(dict(name=name,mimeType='application/json',buffer=json.dumps(data,ensure_ascii=False).encode()));ready(p)
  def export(p,i):
   with p.expect_download() as dl:p.locator(f'#photo-export-{i}').click()
   ready(p);return json.loads(Path(dl.value.path()).read_text())
  def verify(p,*values):
   p.locator('#photo-verify').set_input_files([dict(name=f'branch-{i}.json',mimeType='application/json',buffer=json.dumps(v,ensure_ascii=False).encode()) for i,v in enumerate(values)]);ready(p)
   assert 'Verified' in p.locator('#photo-maintenance-status').inner_text()
  def click(p,selector):p.locator(selector).click();ready(p)
  def seed(p,data,old=None):
   p.evaluate('([k,l,o,d,a])=>{localStorage.clear();localStorage.setItem(l,JSON.stringify(d));if(a!==null)localStorage.setItem(o,JSON.stringify(a))}',[KEY,LEGACY,OLD,data,old]);p.reload();ready(p)
  def usage(p):return p.evaluate('()=>{const entries=Object.keys(localStorage).map(k=>({key:k,characters:k.length+localStorage.getItem(k).length}));return {entries,utf16Bytes:entries.reduce((s,r)=>s+2*r.characters,0)}}')
  ctx=context();p=page(ctx);ready(p)
  original=seed_data()
  # Actual synthetic PNG with sufficient size to make legacy duplication measurable.
  image=p.evaluate("""()=>{const c=document.createElement('canvas');c.width=c.height=128;const x=c.getContext('2d'),d=x.createImageData(128,128);let n=7;for(let i=0;i<d.data.length;i++){n=(n*1664525+1013904223)>>>0;d.data[i]=i%4===3?255:n>>>24}x.putImageData(d,0,0);return c.toDataURL('image/png')}""")
  for a in ['listening','collection','live']:
   for r in original[a]:r['photo']=image
  seed(p,original);initial=state(p);click(p,'#photo-cleanup');assert state(p)==initial
  current=export(p,0);old=export(p,1);assert current==old==original
  bad=copy.deepcopy(current);bad['live'][0]['memo']='incorrect file readback';use(p,'#photo-verify',bad);click(p,'#photo-cleanup');assert state(p)==initial
  verify(p,current,old);click(p,'#photo-cleanup');assert state(p)==initial # Must reload first.
  p.reload();ready(p);verify(p,current,old)
  p.evaluate('failJournal=true');click(p,'#photo-cleanup');assert state(p)==initial
  p.evaluate('failJournal=false');before=usage(p)
  # Interrupt immediately after localStorage deletion, before controller state is updated.
  p.evaluate('interruptRemove=true');click(p,'#photo-cleanup')
  assert raw(p,LEGACY) is None and raw(p)==initial[0]
  p.close();p=page(ctx);ready(p);after=usage(p)
  assert not p.evaluate('review.conflict()') and p.evaluate('review.db()')==original
  for a in ['listening','collection','live']:
   p.evaluate('(a)=>review.section(a)',a);p.locator('#library img').first.wait_for();p.wait_for_function("document.querySelector('#library img')?.naturalWidth>0")
  measurements.append(dict(case='6 records / one generated 128px PNG repeated',before=before,after=after,releasedUTF16Bytes=before['utf16Bytes']-after['utf16Bytes']))
  print('PASS cleanup gates, journal-write failure, interruption after deletion + reload/photos')
  print('USAGE',json.dumps(measurements[-1],ensure_ascii=False))
  updated=copy.deepcopy(original);updated['live'][0]['memo']='保存再開'
  assert p.evaluate('(d)=>review.save(d)',updated)
  # A real old-main tab recreates v03 after cleanup, from its own import UI.
  oldtab=page(ctx,'/legacy');diverged=copy.deepcopy(original);diverged['live'][0]['memo']='旧版からの保存';diverged['live'][0]['photo']='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyIiBoZWlnaHQ9IjIiPjwvc3ZnPg=='
  oldtab.locator('#import-json').set_input_files(dict(name='old.json',mimeType='application/json',buffer=json.dumps(diverged).encode()))
  oldtab.wait_for_function('(k)=>localStorage.getItem(k)!==null',arg=LEGACY)
  p.wait_for_function('review.conflict()');frozen=state(p)
  assert not p.evaluate('review.save({...review.db(),live:[]})');click(p,'#photo-cleanup');assert state(p)==frozen
  # Clear test-induced unsaved draft by reload; conflict persists.
  p.reload();ready(p);assert p.evaluate('review.conflict()')
  new_backup=export(p,0);old_backup=export(p,1);assert new_backup==updated and old_backup==diverged
  use(p,'#photo-recovery-file',old_backup);click(p,'#photo-recover');assert state(p)==frozen # no file proofs
  verify(p,new_backup);click(p,'#photo-recover');assert state(p)==frozen # both backups required
  verify(p,new_backup,old_backup)
  p.evaluate('failPhoto=true');click(p,'#photo-recover');assert state(p)==frozen
  p.evaluate('failPhoto=false')
  p.evaluate('failRef=true');click(p,'#photo-recover');assert state(p)==frozen
  p.evaluate('failRef=false');click(p,'#photo-recover')
  assert p.evaluate('review.db()')==diverged and not p.evaluate('review.conflict()')
  assert raw(p,LEGACY)==frozen[1]
  resumed=copy.deepcopy(diverged);resumed['listening'][0]['memo']='recovered save'
  assert p.evaluate('(d)=>review.save(d)',resumed)
  with p.expect_download() as dl:p.locator('#export-json').click()
  roundtrip=json.loads(Path(dl.value.path()).read_text());assert roundtrip==resumed
  use(p,'#import-json',roundtrip);assert p.evaluate('review.db()')==resumed
  p.set_viewport_size({'width':390,'height':844});p.locator('#photo-maintenance').screenshot(path=str(evidence/'recovery-panel.png'))
  print('PASS actual old main saves after cleanup; dual backups; failed recovery retains both; recovery/save/JSON roundtrip')
  oldtab.close();ctx.close()
  # Before cleanup, one legacy key matches, the other is distinct and must be kept.
  ctx=context();p=page(ctx);ready(p)
  legacy_v1=[dict(id='old-mbid',title='v1 preserved',artist='Synthetic',photo=image,rating='4')]
  seed(p,original,legacy_v1);p.reload();ready(p)
  backups=[export(p,i) for i in [0,1,2]];verify(p,*backups);click(p,'#photo-cleanup')
  assert raw(p,LEGACY) is None and json.loads(raw(p,OLD))==legacy_v1
  p.reload();ready(p);assert not p.evaluate('review.conflict()')
  print('PASS only matching v03 removed; distinct v1 retained and independently exportable/readback verified')
  ctx.close()
  # Legacy v1 without entry IDs: deterministic migration/export allows exact readback.
  ctx=context();p=page(ctx);ready(p)
  p.evaluate('([k,d])=>{localStorage.clear();localStorage.setItem(k,JSON.stringify(d))}',[OLD,legacy_v1]);p.reload();ready(p)
  b=export(p,0);v1=export(p,2);assert b==v1
  p.reload();ready(p);verify(p,b);click(p,'#photo-cleanup');assert raw(p,OLD) is None
  p.reload();ready(p);assert p.evaluate('review.db()')==b
  print('PASS v1 missing-ID migration: stable export/readback, cleanup and reload')
  ctx.close()
  # A crash between two deletions must stop writes, without losing either branch.
  ctx=context();p=page(ctx);ready(p);seed(p,original,original);p.reload();ready(p)
  backup=export(p,0);verify(p,backup);p.evaluate('interruptRemove=true');click(p,'#photo-cleanup')
  assert raw(p,LEGACY) is None and raw(p,OLD) is not None
  p.reload();ready(p);assert p.evaluate('review.conflict()')
  assert not p.evaluate('review.save(review.db())')
  p.reload();ready(p);verify(p,backup);use(p,'#photo-recovery-file',backup);click(p,'#photo-recover')
  assert p.evaluate('review.db()')==original and not p.evaluate('review.conflict()')
  assert p.evaluate('review.save(review.db())')
  p.reload();ready(p);verify(p,backup);click(p,'#photo-cleanup');assert raw(p,OLD) is None
  p.reload();ready(p);assert not p.evaluate('review.conflict()')
  print('PASS partial two-key deletion interrupted; durable stop/recovery/retry cleanup')
  ctx.close()
  # A real old main write BEFORE cleanup must preserve new and old snapshots too.
  ctx=context();p=page(ctx);ready(p);seed(p,original);p.reload();ready(p)
  oldtab=page(ctx,'/legacy');oldtab.locator('#import-json').set_input_files(dict(name='old-before.json',mimeType='application/json',buffer=json.dumps(diverged).encode()))
  p.wait_for_function('review.conflict()');frozen=state(p);click(p,'#photo-cleanup');assert state(p)==frozen
  backups=[export(p,i) for i in [0,1]];verify(p,*backups);use(p,'#photo-recovery-file',backups[0]);click(p,'#photo-recover')
  assert p.evaluate('review.db()')==original and p.evaluate('review.save(review.db())')
  oldtab.close();ctx.close()
  print('PASS actual old main write before cleanup; both backups and explicit new-branch recovery')
  # A source update while cleanup is awaiting its durable intent must stop deletion.
  ctx=context();p=page(ctx);ready(p);seed(p,original);p.reload();ready(p)
  b=export(p,0);verify(p,b);p.evaluate('pauseCleanup=true')
  p.locator('#photo-cleanup').click();p.wait_for_function('!!window.resumeCleanup')
  locked=page(ctx,'/legacy');locked.locator('#import-json').set_input_files(dict(name='locked-old.json',mimeType='application/json',buffer=json.dumps(diverged).encode()));locked.locator('#save-notice').wait_for(state='visible');assert json.loads(raw(p,LEGACY))==original;locked.close()
  q=page(ctx);ready(q)
  q.evaluate('([k,d])=>localStorage.setItem(k,JSON.stringify(d))',[LEGACY,diverged])
  p.wait_for_function('(k)=>JSON.parse(localStorage.getItem(k))?.live[0].memo==="旧版からの保存"',arg=LEGACY);p.wait_for_function('review.conflict()');assert json.loads(raw(p,LEGACY))==diverged
  p.evaluate('resumeCleanup()');ready(p)
  assert json.loads(raw(p,LEGACY))==diverged and p.evaluate('review.db()')==original
  p.reload();ready(p);assert p.evaluate('review.conflict()')
  backups=[export(p,i) for i in [0,1]];verify(p,*backups);use(p,'#photo-recovery-file',backups[0]);click(p,'#photo-recover')
  assert not p.evaluate('review.conflict()') and p.evaluate('review.db()')==original
  assert p.evaluate('review.save(review.db())')
  print('PASS legacy race before cleanup; durable stop on reload; choose new branch recovery/save')
  # Source changes while a reviewed recovery is copying: do not publish stale choice.
  q.evaluate('([k,d])=>localStorage.setItem(k,JSON.stringify(d))',[LEGACY,original]);p.reload();ready(p)
  bs=[export(p,i) for i in [0,1]];verify(p,*bs);use(p,'#photo-recovery-file',bs[0]);new_before=raw(p)
  p.evaluate('pauseRecovery=true');p.locator('#photo-recover').click();p.wait_for_function('!!window.resumeRecovery')
  q.evaluate('([k,d])=>localStorage.setItem(k,JSON.stringify(d))',[LEGACY,diverged]);p.wait_for_function('(k)=>JSON.parse(localStorage.getItem(k))?.live[0].memo==="旧版からの保存"',arg=LEGACY);p.wait_for_function('review.conflict()')
  p.evaluate('resumeRecovery()');ready(p);assert raw(p)==new_before and json.loads(raw(p,LEGACY))==diverged
  p.reload();ready(p);bs=[export(p,i) for i in [0,1]];verify(p,*bs);use(p,'#photo-recovery-file',bs[1]);click(p,'#photo-recover')
  assert p.evaluate('review.db()')==diverged and p.evaluate('review.save(review.db())')
  print('PASS source race during recovery stops publication; fresh dual backups allow retry')
  q.close();ctx.close()
  # No headroom for old JSON and new manifest simultaneously. Do not pre-delete old.
  ctx=context();p=page(ctx);ready(p)
  p.evaluate('([k,d])=>{localStorage.clear();localStorage.setItem(k,JSON.stringify(d));const n=Object.keys(localStorage).reduce((s,k)=>s+k.length+localStorage.getItem(k).length,0);sessionStorage.setItem("cap",String(n))}',[LEGACY,original])
  legacy_raw=raw(p,LEGACY);p.reload();ready(p)
  assert p.evaluate('review.failed()') and raw(p) is None and raw(p,LEGACY)==legacy_raw
  assert '容量' in p.locator('#storage-reason').inner_text()
  click(p,'#photo-cleanup');assert raw(p,LEGACY)==legacy_raw
  rescued=export(p,1);verify(p,rescued);assert rescued==original
  use(p,'#photo-recovery-file',rescued);click(p,'#photo-recover');assert raw(p) is None and raw(p,LEGACY)==legacy_raw
  target=context();dest=page(target);ready(dest);use(dest,'#import-json',rescued)
  assert dest.evaluate('review.db()')==original
  dest.reload();ready(dest);assert dest.evaluate('review.db()')==original
  assert raw(p,LEGACY)==legacy_raw
  print('PASS aggregate localStorage quota blocks coexistence; old retained; export/readback + restore to isolated context')
  target.close();ctx.close();browser.close()
 assert not errors,errors
 (evidence/'usage.json').write_text(json.dumps(measurements,ensure_ascii=False,indent=2)+'\n')
 server.shutdown();print('PASS all next-stage synthetic recovery checks')
if __name__=='__main__':main()

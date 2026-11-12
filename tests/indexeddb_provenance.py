"""Migration-source provenance across edits; isolated Chromium and synthetic photos only."""
import copy, hashlib, json, os, subprocess, threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
from ui_v0322 import ROOT, QuietHandler
from lifecycle_harness import controls
from data_preservation import seed_data, PHOTO
from indexeddb_recovery import KEY, LEGACY, OLD, SEAM, INJECT


def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
 url=f'http://127.0.0.1:{server.server_port}'
 source=(ROOT/'index.html').read_text().replace("setSection('listening');showStorageState();",SEAM+controls()+"setSection('listening');showStorageState();")
 legacy_source=subprocess.check_output(['git','show','c2c719d:index.html'],cwd=ROOT).decode()
 evidence=Path(os.environ.get('MLA_PROVENANCE_EVIDENCE',ROOT/'docs/indexeddb-provenance-evidence'));evidence.mkdir(exist_ok=True)
 errors=[];cases=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
  def fresh():
   ctx=browser.new_context(accept_downloads=True,locale='ja-JP')
   ctx.route(url+'/',lambda r:r.fulfill(body=source,content_type='text/html'))
   ctx.route(url+'/legacy',lambda r:r.fulfill(body=legacy_source,content_type='text/html'))
   ctx.route('https://**/*',lambda r:r.abort());ctx.add_init_script(INJECT)
   p=ctx.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept());p.goto(url);ready(p)
   return ctx,p
  def ready(p):p.wait_for_function('window.review && !review.busy()')
  def raw(p,k=KEY):return p.evaluate('(k)=>localStorage.getItem(k)',k)
  def seed(p,data,other=None):
   p.evaluate('([l,o,d,a])=>{localStorage.clear();localStorage.setItem(l,JSON.stringify(d));if(a!==null)localStorage.setItem(o,JSON.stringify(a))}',[LEGACY,OLD,data,other]);p.reload();ready(p)
  def click(p,selector):p.locator(selector).click();ready(p)
  def export(p,index):
   with p.expect_download() as dl:p.locator(f'#photo-export-{index}').click()
   ready(p);return json.loads(Path(dl.value.path()).read_text())
  def files(p,*values):
   p.locator('#photo-verify').set_input_files([dict(name=f'saved-{i}.json',mimeType='application/json',buffer=json.dumps(v,ensure_ascii=False).encode()) for i,v in enumerate(values)]);ready(p)
   assert 'Verified' in p.locator('#photo-maintenance-status').inner_text()
  def save(p,data,kind='edit'):assert p.evaluate('([d,k])=>review.save(d,{kind:k})',[data,kind])
  def proof(p):return json.loads(raw(p))['importedLegacy']
  def edited(data):
   result=copy.deepcopy(data)
   for area in ['listening','collection','live']:
    result[area][0]['memo']='新版だけで編集 '+area
    result[area][0]['title']+=' edited'
    result[area][0]['photo']='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyIiBoZWlnaHQ9IjIiPjwvc3ZnPg=='
    result[area].append(dict(result[area][0],entryId=area+'-added',title='新版追加 '+area,photo=PHOTO))
   return result
  original=seed_data()
  ctx,p=fresh();unrelated=[dict(id='unrelated',title='Unimported',artist='Synthetic',rating='4',photo=PHOTO)]
  seed(p,original,unrelated);legacy_raw=raw(p,LEGACY);other_raw=raw(p,OLD)
  imported=proof(p)
  assert imported==dict(version=1,sources=[dict(key=LEGACY,sha256='sha256-'+hashlib.sha256(legacy_raw.encode()).hexdigest())])
  modified=edited(original);save(p,modified,'create');assert proof(p)==imported
  # Current file alone is insufficient once old and new differ.
  p.reload();ready(p);new=export(p,0);old=export(p,1);other=export(p,2)
  assert new==modified and old==original
  files(p,new);before=raw(p);click(p,'#photo-cleanup');assert raw(p,LEGACY)==legacy_raw and raw(p)==before
  # Previously exported pre-edit JSON cannot stand in for the latest new snapshot.
  files(p,new,old,other)
  again=copy.deepcopy(modified);again['live'][0]['memo']='再編集';save(p,again)
  click(p,'#photo-cleanup');assert raw(p,LEGACY)==legacy_raw # Reload required after each save.
  p.reload();ready(p);p.locator('#photo-verify').set_input_files(dict(name='stale-new.json',mimeType='application/json',buffer=json.dumps(new).encode()));ready(p);click(p,'#photo-cleanup');assert raw(p,LEGACY)==legacy_raw # New receipt stale.
  latest=export(p,0);files(p,latest,old,other)
  frozen=raw(p);p.evaluate('failJournal=true');click(p,'#photo-cleanup');assert raw(p)==frozen and raw(p,LEGACY)==legacy_raw
  p.evaluate('failJournal=false');click(p,'#photo-cleanup');assert raw(p,LEGACY) is None and raw(p,OLD)==other_raw
  assert raw(p)==frozen
  p.reload();ready(p);assert not p.evaluate('review.conflict()') and p.evaluate('review.db()')==again
  for area in ['listening','collection','live']:
   p.evaluate('(a)=>review.section(a)',area);p.wait_for_function("document.querySelector('#library img')?.naturalWidth>0")
  assert export(p,0)==again
  cases.append(dict(case='new-only add/edit/photos all three areas',sourceProof=imported,legacyDeleted=True,unimportedLegacyRetained=True,currentCounts={a:len(again[a]) for a in ['listening','collection','live']}))
  print('PASS new-only add/edit/photo changes: provenance carried; latest JSON/reload gates; imported key deleted, unrelated key retained')
  ctx.close()
  # Actual old-main write after new-only edits: both branches must survive and export.
  ctx,p=fresh();seed(p,original);save(p,modified);p.reload();ready(p)
  new=export(p,0);old=export(p,1);files(p,new,old)
  oldtab=ctx.new_page();oldtab.on('pageerror',lambda e:errors.append(str(e)));oldtab.on('dialog',lambda d:d.accept());oldtab.goto(url+'/legacy')
  branched=copy.deepcopy(original);branched['collection'][0]['memo']='旧版でも保存';branched['live'][0]['photo']=modified['live'][0]['photo']
  oldtab.locator('#import-json').set_input_files(dict(name='old-save.json',mimeType='application/json',buffer=json.dumps(branched).encode()))
  p.wait_for_function('(k)=>JSON.parse(localStorage.getItem(k)).collection[0].memo==="旧版でも保存"',arg=LEGACY)
  p.wait_for_function('review.conflict()');frozen=raw(p);legacy_changed=raw(p,LEGACY)
  click(p,'#photo-cleanup');assert raw(p)==frozen and raw(p,LEGACY)==legacy_changed
  assert not p.evaluate('review.save(review.db())')
  p.reload();ready(p);assert p.evaluate('review.conflict()')
  assert export(p,0)==modified and export(p,1)==branched
  files(p,modified,branched);click(p,'#photo-cleanup');assert raw(p)==frozen and raw(p,LEGACY)==legacy_changed
  print('PASS actual old-main save after new edits: cleanup/save stopped across reload; both complete photo JSON branches exported')
  # Explicit new-branch adoption must not re-authorize deletion of changed old sources.
  p.locator('#photo-recovery-file').set_input_files(dict(name='adopt-new.json',mimeType='application/json',buffer=json.dumps(modified).encode()));ready(p);click(p,'#photo-recover')
  assert proof(p)['sources']==[] and p.evaluate('review.db()')==modified
  p.reload();ready(p);files(p,modified,branched);click(p,'#photo-cleanup');assert raw(p,LEGACY)==legacy_changed
  cases.append(dict(case='old-main save too',cleanupStopped=True,bothPhotoBackupsMatch=True,afterRecoverySources=proof(p)['sources']))
  print('PASS explicit recovery resets provenance; rejected old branch stays retained')
  ctx.close()
  # Legacy prototypes: establish only equivalence that can still be proved before editing.
  for already_edited in [False,True]:
   ctx,p=fresh();seed(p,original)
   if already_edited:save(p,modified)
   p.evaluate('(k)=>{const d=JSON.parse(localStorage.getItem(k));delete d.importedLegacy;localStorage.setItem(k,JSON.stringify(d))}',KEY)
   p.reload();ready(p);save(p,modified);p.reload();ready(p)
   files(p,export(p,0),export(p,1));click(p,'#photo-cleanup')
   assert (raw(p,LEGACY) is None)==(not already_edited)
   print('PASS pre-provenance compatibility: '+('already edited history not invented; old retained' if already_edited else 'equivalence verified before first edit; cleanup allowed'))
   ctx.close()
  # Source digest is checked independently of the combined conflict stamp.
  ctx,p=fresh();seed(p,original);save(p,modified)
  p.evaluate('''async ([k,l,d])=>{const old=JSON.stringify(d);localStorage.setItem(l,old);const packed=JSON.parse(localStorage.getItem(k));packed.legacyStamp=await MLAPhotos.idFor(JSON.stringify([old,null]));localStorage.setItem(k,JSON.stringify(packed))}''',[KEY,LEGACY,branched])
  p.reload();ready(p);assert not p.evaluate('review.conflict()')
  files(p,export(p,0),export(p,1));before=raw(p,LEGACY);click(p,'#photo-cleanup');assert raw(p,LEGACY)==before
  print('PASS per-key content digest rejects changed legacy even when combined stamp agrees')
  ctx.close()
  # Invalid source evidence never falls back to a weaker content assumption.
  ctx,p=fresh();seed(p,original)
  p.evaluate('(k)=>{const d=JSON.parse(localStorage.getItem(k));d.importedLegacy.sources[0].sha256="bad";localStorage.setItem(k,JSON.stringify(d))}',KEY)
  p.reload();ready(p);files(p,export(p,0),export(p,1));before=raw(p,LEGACY);click(p,'#photo-cleanup');assert raw(p,LEGACY)==before
  print('PASS malformed provenance stops cleanup without deleting old data')
  ctx.close();browser.close()
 assert not errors,errors
 (evidence/'cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n')
 server.shutdown();print('PASS all migration-provenance checks')
if __name__=='__main__':main()

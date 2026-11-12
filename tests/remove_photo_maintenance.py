"""Production backup controls under failure; no historical UI harness in this suite."""
import copy, json, os, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from ui_v0322 import ROOT, QuietHandler, edit
from data_preservation import seed_data
from indexeddb_recovery import KEY, LEGACY, OLD, SEAM, INJECT

OUT=ROOT/'docs/remove-photo-maintenance-evidence'


def main():
 OUT.mkdir(exist_ok=True)
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
 threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/'
 source=(ROOT/'index.html').read_text().replace("setSection('listening');showStorageState();",SEAM+"setSection('listening');showStorageState();")
 errors=[]
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  def ready(p):p.wait_for_function('window.review && !review.busy()')
  def fresh():
   c=b.new_context(accept_downloads=True);c.route(url,lambda r:r.fulfill(body=source,content_type='text/html'));c.route('https://**/*',lambda r:r.abort());c.add_init_script(INJECT+"""
const read=IDBObjectStore.prototype.get;
IDBObjectStore.prototype.get=function(...a){if(sessionStorage.getItem('failRead')==='yes'&&this.transaction.db.name==='mla-photos-v1')throw Error('synthetic IDB read failure');return read.apply(this,a)};
""")
   c.add_init_script('localStorage.setItem("mma-ui-language",'+json.dumps(os.environ.get('MLA_TEST_LANGUAGE','en'))+')')
   p=c.new_page();p.on('pageerror',lambda e:errors.append(str(e)));answers=[];alerts=[]
   def dialog(d):
    if d.type=='prompt':
     answer=answers.pop(0) if answers else None
     if answer is None:d.dismiss()
     else:d.accept(answer)
    else:alerts.append(d.message);d.accept()
   p.on('dialog',dialog);p.goto(url);ready(p);return c,p,answers,alerts
  def seed(p):
   p.evaluate('([k,d])=>localStorage.setItem(k,JSON.stringify(d))',[LEGACY,seed_data()]);p.reload();ready(p)
  def raw(p):return p.evaluate('ks=>ks.map(k=>localStorage.getItem(k))',[KEY,LEGACY,OLD])
  def export(p,answers,index=None):
   if index is not None:answers.append(str(index))
   with p.expect_download() as d:p.locator('#export-json').click()
   return Path(d.value.path()).read_bytes()
  def restore(p,answers,files,choice='1'):
   answers.append(choice);p.locator('#import-json').set_input_files([dict(name=f'branch-{i}.json',mimeType='application/json',buffer=f) for i,f in enumerate(files)]);ready(p)
  # Actual alternate-tab source write; normal UI remains free of maintenance controls.
  c,p,answers,alerts=fresh();seed(p);original=seed_data()
  edit(p,'listening');p.locator('#memo').fill('new side');p.locator('#save').click();ready(p)
  new=p.evaluate('review.db()');q=c.new_page();q.goto(url);ready(q)
  branched=copy.deepcopy(original);branched['live'][0]['memo']='old side'
  q.evaluate('([k,v])=>localStorage.setItem(k,JSON.stringify(v))',[LEGACY,branched]);p.wait_for_function('review.conflict()')
  before=raw(p);new_file=export(p,answers,0);old_file=export(p,answers,1)
  assert json.loads(new_file)==new and json.loads(old_file)==branched
  assert not p.evaluate('review.save(review.db())');assert raw(p)==before
  p.reload();ready(p)
  # One branch is insufficient: no storage change even after adoption confirmation.
  restore(p,answers,[new_file]);assert raw(p)==before
  restore(p,answers,[new_file,old_file],None);assert raw(p)==before
  p.evaluate('failRef=true');restore(p,answers,[new_file,old_file]);assert raw(p)==before
  p.evaluate('failRef=false')
  adopted=copy.deepcopy(new);adopted['live'][0]['memo']='reviewed combined candidate'
  adopted['live'][0]['photo']=p.evaluate("()=>{const c=document.createElement('canvas');c.width=c.height=7;return c.toDataURL()}")
  candidate=json.dumps(adopted).encode()
  p.evaluate('failPhoto=true');restore(p,answers,[new_file,old_file,candidate],'3');assert raw(p)==before
  p.evaluate('failPhoto=false');restore(p,answers,[new_file,old_file,candidate],'3');assert p.evaluate('review.db()')==adopted
  assert raw(p)[1:]==before[1:] # No cleanup, no old-key removal.
  p.reload();ready(p);assert not p.evaluate('review.conflict()')
  assert json.loads(export(p,answers))==adopted
  print('PASS production controls: branch export exact, save stop, missing backup/cancel/failed recovery preserve both, retry/reload success; legacy retained',flush=True)
  envelope=p.evaluate('ks=>MLARescue.collect(ks,null)',[KEY,LEGACY,OLD])
  assert set(v['data'] for v in envelope['photos'].values())=={r['photo'] for a in ['listening','collection','live'] for r in adopted[a]}
  assert all(not s['changed'] for s in envelope['sources'])
  print('PASS raw recovery envelope includes exact readable photo bytes and all sources',flush=True)
  c.close()
  # Reading and content-integrity failures: readable old branch and all raw sources survive.
  for failure in ['read','mismatch']:
   c,p,answers,alerts=fresh();seed(p);before=raw(p)
   if failure=='read':p.evaluate("sessionStorage.setItem('failRead','yes')")
   else:
    p.evaluate("""async()=>{await new Promise((resolve,reject)=>{const r=indexedDB.open('mla-photos-v1');r.onsuccess=()=>{const db=r.result,t=db.transaction('photos','readwrite'),s=t.objectStore('photos'),q=s.openCursor();q.onsuccess=()=>{const c=q.result;if(c){c.update('corrupt bytes');c.continue()}};t.oncomplete=()=>{db.close();resolve()};t.onabort=()=>reject(t.error)}})}""")
   p.reload();ready(p);assert p.evaluate('review.failed()');assert raw(p)==before
   old_file=export(p,answers,1);assert json.loads(old_file)==original
   with p.expect_download() as d:p.locator('#recover-source').click()
   envelope=json.loads(Path(d.value.path()).read_text());assert envelope['format']=='mla-recovery-sources'
   assert [s['raw'] for s in envelope['sources']]==before
   assert any(v.get('error') for v in envelope['photos'].values())
   assert raw(p)==before
   dest,dp,da,_=fresh();empty=raw(dp)
   dp.locator('#import-json').set_input_files(dict(name='raw-recovery.json',mimeType='application/json',buffer=json.dumps(envelope).encode()));ready(dp)
   assert raw(dp)==empty # Raw recovery is never accepted as a portable backup.
   restore(dp,da,[old_file]);dp.reload();ready(dp)
   assert dp.evaluate('review.db()')==original
   assert all(dp.locator('#library img').evaluate_all('(ns)=>ns.map(n=>n.complete&&n.naturalWidth>0)'))
   assert raw(p)==before
   dest.close();c.close();print('PASS',failure,'startup stops, raw new/old retained, unavailable photos explicit, old portable JSON restores into isolated context',flush=True)
  # Failed write keeps current input and selected file. Existing injected-photo suite
  # additionally tests the no-photo fallback/cancel path and immutable reference publication.
  c,p,answers,alerts=fresh();seed(p);edit(p,'listening');p.locator('#memo').fill('must retain input');before=raw(p)
  p.evaluate('failRef=true');p.locator('#save').click();ready(p)
  assert p.locator('#memo').input_value()=='must retain input' and raw(p)==before
  p.evaluate('failRef=false');p.locator('#save-return').click();p.locator('#save').click();ready(p)
  assert p.evaluate('review.db().listening[0].memo')=='must retain input'
  assert raw(p)[1:]==before[1:];c.close()
  print('PASS localStorage failure preserves draft input/source, retry succeeds',flush=True)
  b.close()
 assert not errors,errors
 server.shutdown();print('PASS production stopped-state recovery without maintenance UI',flush=True)


if __name__=='__main__':main()

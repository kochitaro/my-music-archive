"""Actual form CRUD and photo controls after migration; synthetic local-only data."""
import base64, json, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, QuietHandler, edit
from data_preservation import seed_data, PHOTO
from indexeddb_photos import KEY, LEGACY, SEAM


def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 source=(ROOT/'index.html').read_text().replace("setSection('listening');showStorageState();",SEAM+"setSection('listening');showStorageState();")
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  c=b.new_context(accept_downloads=True);url=f'http://127.0.0.1:{server.server_port}/'
  c.route(url,lambda r:r.fulfill(body=source,content_type='text/html'))
  c.route('https://**/*',lambda r:r.abort())
  p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept())
  p.goto(url);p.wait_for_function('window.probe')
  original=seed_data();p.evaluate('([k,d])=>localStorage.setItem(k,JSON.stringify(d))',[LEGACY,original]);p.reload()
  def ready():p.wait_for_function('window.probe && !probe.busy()')
  def data():return p.evaluate('probe.db()')
  def upload(selector,second=False):
   # Distinct valid generated PNG, through the actual resize/file input path.
   photo=p.evaluate('''second=>{const x=document.createElement('canvas');x.width=x.height=8;const c=x.getContext('2d');c.fillStyle=second?'red':'blue';c.fillRect(0,0,8,8);return x.toDataURL()}''',second)
   p.locator(selector).set_input_files(dict(name='synthetic.png',mimeType='image/png',buffer=base64.b64decode(photo.split(',')[1])))
  ready()
  for area in ['listening','collection','live']:
   p.locator(f'[data-section={area}]').click();title='UI '+area
   if area=='live':
    p.locator('#add-live-trigger').click();p.locator('#live-title').fill(title);upload('#live-photo');p.locator('#live-form button[type=submit],#live-form > button').click()
   else:
    p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill(title);p.locator('#manual-artist').fill('Synthetic artist');upload('#album-photo');p.locator('#save').click()
   ready();created=next(r for r in data()[area] if r['title']==title);assert created['photo'].startswith('data:image/')
   edit(p,title);p.locator('#memo').fill('UI edited');upload('#e-live-photo' if area=='live' else '#album-photo',True);p.locator('#save').click();ready()
   updated=next(r for r in data()[area] if r['title']==title);assert updated['memo']=='UI edited' and updated['photo']!=created['photo']
   edit(p,title);p.locator('#remove-photo' if area=='live' else '#remove-album-photo').click();ready()
   assert next(r for r in data()[area] if r['title']==title)['photo']==''
   p.locator('#close').click();edit(p,title);upload('#e-live-photo' if area=='live' else '#album-photo');p.locator('#save').click();ready()
   assert next(r for r in data()[area] if r['title']==title)['photo']
   edit(p,title);p.locator('#delete').click();p.locator('#delete-accept').click();ready()
   assert all(r['title']!=title for r in data()[area])
   assert data()[area]==original[area]
   print('PASS UI',area,'create with photo, edit, replace/remove/add photo, delete; original records exact',flush=True)
  expected=data()
  with p.expect_download() as d:p.locator('#export-json').click()
  saved=Path(d.value.path()).read_bytes();assert json.loads(saved)==expected
  p.locator('#import-json').set_input_files(dict(name='actual-export.json',mimeType='application/json',buffer=saved));ready()
  p.reload();ready();assert data()==expected
  assert not errors,errors
  print('PASS actual downloaded photo JSON import/reload exact; page errors 0',flush=True)
  b.close()
 server.shutdown()


if __name__=='__main__':main()

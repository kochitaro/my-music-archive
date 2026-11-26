"""Legal page navigation and storage isolation; synthetic data, blocked external traffic."""
import json, os, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler
from data_preservation import seed_data

OUT=Path(os.environ.get('MLA_LEGAL_OUTPUT',str(ROOT/'docs/legal-pages-final'))); OUT.mkdir(exist_ok=True)
SNAPSHOT='''async()=>{
 const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('mla-archive-v1');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
 try{return await new Promise((resolve,reject)=>{const names=[...db.objectStoreNames],out={},tx=db.transaction(names,'readonly');for(const name of names){const store=tx.objectStore(name);store.getAllKeys().onsuccess=e=>{out[name]={keys:e.target.result};store.getAll().onsuccess=e=>out[name].values=e.target.result}}tx.oncomplete=()=>resolve(out);tx.onerror=()=>reject(tx.error)})}finally{db.close()}
}'''
DENY_STORAGE='''(()=>{if(!/\\/(terms|privacy)\\.html$/.test(location.pathname))return;window.storageCalls=[];const deny=()=>{storageCalls.push('attempt');throw Error('Legal document accessed storage')};Object.defineProperty(window,'indexedDB',{get:deny});Object.defineProperty(window,'localStorage',{get:deny});Object.defineProperty(window,'sessionStorage',{get:deny});})();'''

def ready(p):
 p.wait_for_function('!document.querySelector("main").inert')
 p.wait_for_timeout(200)
def snapshot(p):return p.evaluate(SNAPSHOT)
def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
 url=f'http://127.0.0.1:{server.server_port}/'
 with sync_playwright() as pw:
  for engine in ['chromium','webkit']:
   browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if engine=='chromium' else pw.webkit.launch(executable_path=os.environ.get('MLA_WEBKIT'))
   for width in [390,1280]:
    c=browser.new_context(viewport=dict(width=width,height=844),is_mobile=width==390,has_touch=width==390,accept_downloads=True)
    c.route('https://**/*',lambda r:r.abort());c.add_init_script(DENY_STORAGE)
    p=c.new_page();p.on('dialog',lambda d:d.accept());errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    # Empty-browser direct access must not create an IndexedDB database.
    for doc,count in [('terms',13),('privacy',14)]:
     for language in ['ja','en']:
      response=p.goto(url+doc+'.html?lang='+language+'#'+language);assert response.status==200
      expect(p.locator('#'+language)).to_be_visible()
      assert p.locator('#'+language+' > section').count()==count
      assert p.locator('article:visible').count()==1
      assert p.evaluate('storageCalls')==[]
      assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
      for code in ['ja','en']:
       expect(p.locator(f'#{code} a[href="mailto:mylisteningarchive@gmail.com"]')).to_have_count(1)
       expect(p.locator(f'#{code} a[href="https://x.com/MLArchive_"]')).to_have_count(1)
       expect(p.locator(f'#{code} a[href="https://x.com/MLArchive_"]')).to_have_text('@MLArchive_')
      other='en' if language=='ja' else 'ja'
      p.locator(f'[data-language={other}]').click();expect(p.locator('#'+other)).to_be_visible()
      p.go_back();expect(p.locator('#'+language)).to_be_visible()
      p.screenshot(path=str(OUT/f'{engine}-{width}-{doc}-{language}.png'),full_page=True)
      other_doc='privacy' if doc=='terms' else 'terms'
      p.locator(f'#{language} footer a[href^="{other_doc}.html"]').click()
      assert f'/{other_doc}.html' in p.url;expect(p.locator('#'+language)).to_be_visible()
      assert p.evaluate('storageCalls')==[]
    # Seed before the app first initializes IndexedDB; never branch legacy storage later.
    original=seed_data()
    c.add_init_script('if(location.pathname.endsWith("/") && localStorage.getItem('+json.dumps(KEY)+')===null)localStorage.setItem('+json.dumps(KEY)+','+json.dumps(json.dumps(seed_data()))+')')
    p.goto(url);ready(p)
    for language in ['ja','en']:
     p.locator('#ui-language').select_option(language);ready(p)
     for area in ['listening','collection','live']:
      p.locator(f'[data-section={area}]').click();expect(p.locator('#library')).to_contain_text(area)
     p.locator('[data-section=listening]').click()
     for doc in ['terms','privacy']:
      before=snapshot(p);legacy=p.evaluate('JSON.stringify({...localStorage})')
      p.evaluate('scrollTo(0,document.body.scrollHeight)');p.wait_for_timeout(300)
      links=p.locator('.legal-links');bar=p.locator('#archive-toolbar')
      assert links.bounding_box()['y']+links.bounding_box()['height']<=bar.bounding_box()['y']
      langbox=p.locator('.langbar').bounding_box();assert langbox['y']+langbox['height']<=bar.bounding_box()['y']
      assert p.locator('.langbar').evaluate('e=>getComputedStyle(e).justifyContent')=='flex-end'
      p.screenshot(path=str(OUT/f'{engine}-{width}-footer-{language}.png'))
      a=p.locator('#'+doc+'-link');expect(a).to_have_text(('利用規約' if doc=='terms' else 'プライバシーポリシー') if language=='ja' else ('Terms of Service' if doc=='terms' else 'Privacy Policy'))
      a.click();expect(p.locator('#'+language)).to_be_visible();assert p.evaluate('storageCalls')==[]
      if doc=='terms':
       p.locator(f'section[aria-labelledby={language}-9] a').click();expect(p.locator('#'+language)).to_be_visible();assert '/privacy.html' in p.url
      p.locator(f'#{language} header > a').click();ready(p)
      assert snapshot(p)==before,'IndexedDB changed during legal-page round trip'
      assert p.evaluate('JSON.stringify({...localStorage})')==legacy
      assert p.locator('#ui-language').input_value()==language
     # Export/import from the real UI must preserve synthetic records including photos.
     with p.expect_download() as d:p.locator('#export-json').click()
     saved=Path(d.value.path()).read_bytes();assert json.loads(saved)==original
     before=snapshot(p)
     p.locator('#import-json').set_input_files(dict(name='legal-roundtrip.json',mimeType='application/json',buffer=saved));ready(p)
     p.reload();ready(p)
     assert snapshot(p)['archive']==before['archive']
    assert not errors,errors
    print('PASS',engine,width,'ja/en direct URLs; switching/history; storage denied; 13/14 clauses; no overflow; footer/bar; archive/photos; exact IDB navigation; JSON export/import',flush=True)
    c.close()
    # No JavaScript: both complete language versions and anchor switching remain available.
    c=browser.new_context(java_script_enabled=False,viewport=dict(width=width,height=844))
    p=c.new_page()
    for doc,count in [('terms',13),('privacy',14)]:
     p.goto(url+doc+'.html')
     for language in ['ja','en']:
      p.locator(f'[data-language={language}]').click();expect(p.locator('#'+language)).to_be_visible()
      assert p.locator('#'+language+' > section').count()==count
     p.locator('#en header > a').click();assert p.url==url
    print('PASS',engine,width,'JavaScript disabled: both languages, complete clauses, return links',flush=True)
    c.close()
   browser.close()
 server.shutdown()
if __name__=='__main__':main()

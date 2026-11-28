"""Isolated bilingual footer, unchanged UI, and synthetic same-origin upgrade checks."""
import functools,hashlib,json,subprocess,tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright,expect
from static_distribution import SNAPSHOT
from data_preservation import seed_data
from brand_text_metrics import measure,check,accessible_heading
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/footer-copy-cleanup';BASE='59ba527445533f56919f5a569b9796f5970c0e58'
EXPECTED={'en':'Album metadata: MusicBrainz\nCover artwork: Cover Art Archive\nMetadata may be incomplete or inaccurate.','ja':'アルバム情報：MusicBrainz\nジャケット画像：Cover Art Archive\n情報には欠落や誤りが含まれる場合があります。'}
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
servers=[]
def serve(root):
 s=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)));servers.append(s);threading.Thread(target=s.serve_forever,daemon=True).start();return f'http://127.0.0.1:{s.server_port}/'
def state(p):
 v=p.evaluate(SNAPSHOT);v['local'].pop('mma-ui-language',None)
 for db in v['idb'].values():
  db.pop('settings',None);db.pop('meta',None)
 return v
results=[]
with tempfile.TemporaryDirectory() as tmp:
 old=Path(tmp)
 for f in (ROOT/'dist').iterdir():
  (old/f.name).write_bytes(b'' if f.name=='.nojekyll' else subprocess.check_output(['git','show',BASE+':'+f.name],cwd=ROOT))
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  baseline=serve(old)
  for kind in ['source','dist']:
   base=serve(ROOT if kind=='source' else ROOT/'dist')
   for width in [320,393,1280]:
    c=browser.new_context(viewport={'width':width,'height':852},accept_downloads=True);c.route('https://**/*',lambda r:r.abort())
    p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(base);p.evaluate('MLAReady')
    before=c.new_page();before.goto(baseline);before.evaluate('MLAReady')
    for lang in ['ja','en']:
     for _ in range(3):
      p.select_option('#ui-language',lang);p.select_option('#ui-language','en' if lang=='ja' else 'ja')
     p.select_option('#ui-language',lang);p.wait_for_timeout(300);p.reload();p.evaluate('MLAReady');expect(p.locator('footer.foot')).to_have_text(EXPECTED[lang],use_inner_text=True)
     before.select_option('#ui-language',lang)
     for selector in ['#backup-guide','#page-actions','.legal-links','.langbar','.brand']:
      assert p.locator(selector).inner_html()==before.locator(selector).inner_html(),selector
     style='e=>{const s=getComputedStyle(e);return [s.fontSize,s.color,s.textAlign,s.marginTop,s.marginBottom,s.paddingTop,s.paddingBottom]}'
     assert p.locator('footer.foot').evaluate(style)==before.locator('footer.foot').evaluate(style)
     assert p.locator('footer a').first.evaluate('e=>getComputedStyle(e).color')==before.locator('footer a').first.evaluate('e=>getComputedStyle(e).color')
     assert p.locator('footer a').evaluate_all('els=>els.map(e=>[e.textContent,e.getAttribute("href"),e.target])')==[['MusicBrainz','https://musicbrainz.org/',''],['Cover Art Archive','https://musicbrainz.org/doc/Cover_Art_Archive','']]
     for zoom in [1,2]:
      p.add_style_tag(content=f':root{{font-size:{15*zoom}px}}');p.evaluate('document.fonts.ready');check(measure(p),zoom);accessible_heading(p);p.locator('footer').scroll_into_view_if_needed()
      assert p.locator('footer').evaluate('e=>e.scrollWidth<=e.clientWidth && e.getBoundingClientRect().left>=0 && e.getBoundingClientRect().right<=innerWidth')
      assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')

      results.append(dict(kind=kind,width=width,lang=lang,textScale=zoom,exactCopy=True,noOverflow=True))
     p.add_style_tag(content=':root{font-size:15px}')

    assert not errors,errors;c.close()
  # Same-origin old -> updated document with real imported synthetic records/photos.
  c=browser.new_context(accept_downloads=True);c.route('https://**/*',lambda r:r.abort());p=c.new_page();p.on('dialog',lambda d:d.accept());p.goto(baseline);p.evaluate('MLAReady')
  with p.expect_event('dialog'):p.locator('#import-json').set_input_files({'name':'synthetic.json','mimeType':'application/json','buffer':json.dumps(seed_data()).encode()})
  expect(p.locator('#ui-language')).to_be_enabled()
  def export():
   with p.expect_download() as event:p.locator('#export-json').click()
   return Path(event.value.path()).read_bytes()
  data=export();initial=state(p)
  (old/'index.html').write_bytes((ROOT/'dist/index.html').read_bytes());p.reload();p.evaluate('MLAReady')
  for lang in ['ja','en']*3:
   p.select_option('#ui-language',lang);p.wait_for_timeout(300);p.reload();p.evaluate('MLAReady');assert state(p)==initial;assert export()==data
  preservation={'idbAndRecordsPhotosUnchanged':True,'jsonBytesUnchanged':True,'jsonSHA256':hashlib.sha256(data).hexdigest(),'syntheticCounts':{a:len(seed_data()[a]) for a in ['listening','collection','live']}}
  browser.close()
for s in servers:s.shutdown()
(OUT/'footer-checks.json').write_text(json.dumps({'cases':results,'preservation':preservation},ensure_ascii=False,indent=2))
print('PASS',len(results),'source/dist width/language/text-scale cases; repeated switching/reload; UI/style parity; same-origin synthetic IDB/photos/JSON preservation')

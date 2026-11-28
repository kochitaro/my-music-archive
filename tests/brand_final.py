"""Adopted T-6, exact round-seven parity, retired query/hosts, and synthetic upgrade safety."""
import functools,hashlib,io,json,re,subprocess,tempfile,threading
from pathlib import Path
from urllib.parse import urlsplit
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from PIL import Image,ImageChops
from playwright.sync_api import sync_playwright,expect
from brand_text_metrics import measure,check,accessible_heading
from static_distribution import SNAPSHOT
from data_preservation import seed_data
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brand-logo-02-final';OUT.mkdir(exist_ok=True)
BASE='1504a21fe5f26f13230dde8b6bd2988e6b377db8'
FORBIDDEN=['brand-compare.js','brand-comparison','data-brand-choice','data-brand-symbol','brand-short-name','brand-full-name','--brand-size','logo-compare']
assert not (ROOT/'brand-compare.js').exists()
files=list((ROOT/'dist').iterdir());assert len(files)==20 and not (ROOT/'dist/docs').exists()
for p in files:
 assert p.name!='brand-compare.js'
 if p.suffix in ['.html','.css','.js']:
  text=p.read_text();assert not any(s in text for s in FORBIDDEN),p
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
servers=[]
def serve(root):
 s=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)));servers.append(s);threading.Thread(target=s.serve_forever,daemon=True).start();return f'http://127.0.0.1:{s.server_port}/'
records=[];host_records=[];upgrade={}
with tempfile.TemporaryDirectory(prefix='mla-final-baseline-') as temp:
 old=Path(temp);manifest=json.loads(subprocess.check_output(['git','show',BASE+':docs/brand-logo-02-round7/dist-sha256.json'],cwd=ROOT,text=True))
 for f in manifest:(old/f).write_bytes(b'' if f=='.nojekyll' else subprocess.check_output(['git','show',BASE+':'+f],cwd=ROOT))
 baseline=serve(old)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for kind in ['source','dist']:
   root=ROOT if kind=='source' else ROOT/'dist';base=serve(root)
   for width in [320,375,390,393,430,1280]:
    for lang in ['ja','en']:
     c=browser.new_context(viewport={'width':width,'height':852},locale=lang,is_mobile=width<600,has_touch=width<600);c.route('https://**/*',lambda r:r.abort())
     before=c.new_page();before.goto(baseline);before.evaluate('MLAReady');before.locator('#ui-language').select_option(lang);before.evaluate('document.fonts.ready');old_m=measure(before);old_png=before.locator('.brand').screenshot()
     p=c.new_page();requests=[];p.on('request',lambda r:requests.append(r.url));p.goto(base);p.evaluate('MLAReady');p.locator('#ui-language').select_option(lang);p.evaluate('document.fonts.ready');current=measure(p);check(current);current['accessibility']=accessible_heading(p)
     for key in ['x','y','width','height','size','weight','spacing','lineHeight','color','font','brand','sections','margins','gap']:
      assert current[key]==old_m[key],(kind,width,lang,key,current[key],old_m[key])
     new_png=p.locator('.brand').screenshot();a=Image.open(io.BytesIO(old_png)).convert('RGB');b=Image.open(io.BytesIO(new_png)).convert('RGB');assert a.size==b.size
     diff=ImageChops.difference(a,b);changed=sum(pixel!=(0,0,0) for pixel in diff.getdata());assert changed==0,(kind,width,lang,changed)
     if kind=='source':
      (OUT/f'before-header-{width}-{lang}.png').write_bytes(old_png);(OUT/f'header-{width}-{lang}.png').write_bytes(new_png);p.screenshot(path=str(OUT/f'top-{width}-{lang}.png'))
     query_results=[]
     for suffix in ['?logo-compare=1','?logo-compare=1&brand=M-3']:
      p.goto(base+suffix);p.evaluate('MLAReady');p.evaluate('document.fonts.ready');check(measure(p));assert p.locator('.brand-comparison,[data-brand-choice]').count()==0
      assert p.locator('#page-heading').evaluate('(e)=>e.childElementCount')==0
      assert p.locator('.brand').screenshot()==new_png
      query_results.append(suffix)
     assert not any('brand-compare.js' in u for u in requests),requests
     p.add_style_tag(content=':root{font-size:30px}');check(measure(p),2)
     records.append({'kind':kind,'viewportWidth':width,'lang':lang,'changedHeaderPixels':changed,'queryCases':query_results,**current});c.close()
   # Real app resources at isolated simulated hostnames; no remote account/session is used.
   for host,prefix in [('deploy-preview.my-listening-archive.pages.dev','/'),('ceb7ebd5.my-listening-archive.pages.dev','/'),('localhost','/'),('my-listening-archive.pages.dev','/'),('kochitaro.github.io','/my-music-archive/')]:
    for suffix in ['', '?logo-compare=1']:
     c=browser.new_context(viewport={'width':393,'height':852});c.route('https://**/*',lambda r:r.abort());requests=[];p=c.new_page();p.on('request',lambda r:requests.append(r.url))
     def local(route):
      path=urlsplit(route.request.url).path
      if path.startswith(prefix):path=path[len(prefix):]
      file=root/(path or 'index.html')
      if not file.is_file():route.fulfill(status=404,body='Not found');return
      mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.woff2':'font/woff2','.txt':'text/plain'}.get(file.suffix,'application/octet-stream')
      route.fulfill(body=file.read_bytes(),content_type=mime)
     c.route('https://'+host+'/**',local);p.goto('https://'+host+prefix+suffix);p.evaluate('MLAReady');p.evaluate('document.fonts.ready');check(measure(p));accessible_heading(p)
     assert p.locator('.brand-comparison,[data-brand-choice]').count()==0
     assert not any('brand-compare.js' in u for u in requests)
     host_records.append({'kind':kind,'host':host,'prefix':prefix,'suffix':suffix,'comparisonRequests':0,'panelCount':0});c.close()
  # Same-origin old->new upgrade with synthetic records/photos, including the retired URL.
  c=browser.new_context(viewport={'width':393,'height':852},accept_downloads=True);c.route('https://**/*',lambda r:r.abort());active={'root':old} # use a distinct intercepted origin
  origin='http://127.0.0.1:39991/'
  def app(route):
   file=active['root']/(urlsplit(route.request.url).path.lstrip('/') or 'index.html')
   if not file.is_file():route.fulfill(status=404,body='Not found');return
   route.fulfill(body=file.read_bytes(),content_type={'.html':'text/html','.css':'text/css','.js':'text/javascript','.woff2':'font/woff2','.txt':'text/plain'}.get(file.suffix,'application/octet-stream'))
  c.route(origin+'**',app);p=c.new_page();p.on('dialog',lambda d:d.accept());p.goto(origin);p.evaluate('MLAReady')
  seed=seed_data();seed['listening']=[dict(seed['listening'][0],entryId='final-'+str(i),title='Synthetic album '+str(i)) for i in range(35)]
  with p.expect_event('dialog'):p.locator('#import-json').set_input_files({'name':'synthetic.json','mimeType':'application/json','buffer':json.dumps(seed).encode()})
  expect(p.locator('#ui-language')).to_be_enabled()
  def export():
   with p.expect_download() as event:p.locator('#export-json').click()
   return Path(event.value.path()).read_bytes()
  backup=export();state=p.evaluate(SNAPSHOT);active['root']=ROOT/'dist';requests=[];p.on('request',lambda r:requests.append(r.url));p.goto(origin+'?logo-compare=1');p.evaluate('MLAReady');p.evaluate('document.fonts.ready');check(measure(p));assert p.evaluate(SNAPSHOT)==state;assert export()==backup
  assert not any('brand-compare.js' in u for u in requests)
  for area in ['listening','collection','live']:
   p.locator(f'[data-section={area}]').click();assert p.locator('#library img').first.evaluate('(e)=>e.complete&&e.naturalWidth>0')
   p.locator('#insights-screen').click();expect(p.locator(f'#{area}-insights')).to_be_visible();p.locator('#archive-screen').click()
  assert export()==backup
  upgrade={'from':BASE,'archiveCounts':{a:len(seed[a]) for a in ['listening','collection','live']},'allIdbLocalUnchangedAfterUpgrade':True,'portableJsonSHA256':hashlib.sha256(backup).hexdigest(),'portableJsonUnchanged':True,'comparisonRequests':0};c.close();browser.close()
for s in servers:s.shutdown()
(OUT/'metrics.json').write_text(json.dumps(records,indent=2));(OUT/'host-query-checks.json').write_text(json.dumps(host_records,indent=2));(OUT/'upgrade-safety.json').write_text(json.dumps(upgrade,indent=2))
print('PASS 24 exact baseline cases with zero differing header pixels; 48 retired query cases; 20 host/query cases; 200% text; old->new synthetic DB/local/JSON/photos unchanged; no comparison runtime/assets')

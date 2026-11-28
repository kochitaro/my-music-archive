"""Default brand header acceptance: isolated Chromium, synthetic/empty data, local requests only."""
import functools,json,re,threading,os
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright,expect
from static_distribution import SNAPSHOT
from brand_text_metrics import measure,check,accessible_heading
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/os.environ.get('MLA_BRAND_OUTPUT','docs/brand-logo-02-final/default');OUT.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
servers=[];results=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 for kind in ['source','dist']:
  server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/('dist' if kind=='dist' else '.'))));servers.append(server);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/'
  for width in [320,375,390,393,430,1280]:
   ctx=browser.new_context(viewport={'width':width,'height':900});external=[];ctx.route('https://**/*',lambda r:(external.append(r.request.url),r.abort()))
   page=ctx.new_page();page.goto(base);page.evaluate('MLAReady');page.evaluate('document.fonts.ready');before=page.evaluate(SNAPSHOT)["idb"]
   for lang in ['ja','en']:
    page.locator('#ui-language').select_option(lang)
    expect(page.locator('#page-heading')).to_have_text('My Listening Archive',use_inner_text=True)
    assert page.locator('#page-heading').get_attribute('tabindex')=='-1'
    metrics=measure(page);check(metrics);metrics['accessibility']=accessible_heading(page)
    session=ctx.new_cdp_session(page);session.send('DOM.enable');session.send('CSS.enable');doc=session.send('DOM.getDocument');node=session.send('DOM.querySelector',{'nodeId':doc['root']['nodeId'],'selector':'#page-heading'});fonts=session.send('CSS.getPlatformFontsForNode',{'nodeId':node['nodeId']})['fonts'];session.detach();assert any(f['isCustomFont'] and 'Josefin' in f['familyName'] for f in fonts),fonts
    if kind=='source':page.screenshot(path=str(OUT/f'header-{width}-{lang}.png'))
    for area in ['listening','collection','live']:
     page.locator(f'[data-section={area}]').click();page.locator('#insights-screen').click();expect(page.locator(f'#{area}-insights')).to_be_visible();page.locator('#archive-screen').click()
    after=page.evaluate(SNAPSHOT)["idb"]
    # Language selection intentionally publishes settings and snapshot metadata.
    for name in before:
     assert after[name]['archive']['values'][0]==before[name]['archive']['values'][0]
     assert after[name]['photos']==before[name]['photos']
    results.append({'kind':kind,'viewportWidth':width,'lang':lang,**metrics,'fonts':fonts})
   # Text enlargement must wrap without clipping the service name.
   page.add_style_tag(content=':root{font-size:30px}');check(measure(page),2)
   assert not external,external
   ctx.close()
  for suffix in ['', '?logo-compare=1']:
   ctx=browser.new_context(viewport={'width':320,'height':900});ctx.route('**/*.woff2',lambda r:r.abort());p=ctx.new_page();p.goto(base+suffix);p.evaluate('document.fonts.ready');check(measure(p));accessible_heading(p)
   assert p.locator('.brand-comparison').count()==0
   p.screenshot(path=str(OUT/('fallback-'+kind+'-320-'+('query' if suffix else 'normal')+'.png')));ctx.close()
  print('PASS font blocked: adopted T-6 with and without former query',kind,flush=True)
 browser.close()
for s in servers:s.shutdown()
(OUT/'metrics.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print('PASS 24 width/language/source-dist cases; custom font, fallback, 200%+ text, navigation, no external requests, unchanged archive/photo data (language settings intentionally persist)')

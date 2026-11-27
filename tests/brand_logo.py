"""Default brand header acceptance: isolated Chromium, synthetic/empty data, local requests only."""
import functools,json,re,threading,os
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright,expect
from static_distribution import SNAPSHOT
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/os.environ.get('MLA_BRAND_OUTPUT','docs/brand-logo-02');OUT.mkdir(exist_ok=True)
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
    expect(page.locator('#page-heading')).to_have_text('My Listening Archive')
    assert page.locator('#page-heading').get_attribute('tabindex')=='-1'
    assert page.locator('[data-brand-symbol="B-3"] svg').get_attribute('aria-hidden')=='true'
    assert page.locator('[data-brand-symbol="B-3"] svg path').count()==1
    metrics=page.locator('.brand').evaluate('''e=>{const h=e.querySelector('h1'),s=e.querySelector('[data-brand-symbol="B-3"] svg'),r=h.getBoundingClientRect(),b=s.getBoundingClientRect(),style=getComputedStyle(h);return {font:style.fontFamily,size:style.fontSize,weight:style.fontWeight,spacing:style.letterSpacing,heading:[r.x,r.y,r.width,r.height],symbol:[b.width,b.height],headingOverflow:h.scrollWidth>h.clientWidth,overflow:[...e.querySelectorAll('*')].some(n=>n.getBoundingClientRect().right>innerWidth),bodyFont:getComputedStyle(document.body).fontFamily}}''')
    assert not metrics['overflow'] and not metrics['headingOverflow'],metrics
    assert abs(metrics['symbol'][0]/metrics['symbol'][1]-137.863/211.133)<.002
    assert metrics['heading'][3]<38,metrics # one line at normal text size
    assert 'Josefin' not in metrics['bodyFont']
    session=ctx.new_cdp_session(page);session.send('DOM.enable');session.send('CSS.enable');doc=session.send('DOM.getDocument');node=session.send('DOM.querySelector',{'nodeId':doc['root']['nodeId'],'selector':'#page-heading'});fonts=session.send('CSS.getPlatformFontsForNode',{'nodeId':node['nodeId']})['fonts'];session.detach();assert any(f['isCustomFont'] and 'Josefin' in f['familyName'] for f in fonts),fonts
    if kind=='source':page.screenshot(path=str(OUT/f'header-{width}-{lang}.png'))
    for area in ['listening','collection','live']:
     page.locator(f'[data-section={area}]').click();page.locator('#insights-screen').click();expect(page.locator(f'#{area}-insights')).to_be_visible();page.locator('#archive-screen').click()
    after=page.evaluate(SNAPSHOT)["idb"]
    # Language selection intentionally publishes settings and snapshot metadata.
    for name in before:
     assert after[name]['archive']['values'][0]==before[name]['archive']['values'][0]
     assert after[name]['photos']==before[name]['photos']
    results.append({'kind':kind,'width':width,'lang':lang,**metrics,'fonts':fonts})
   # Text enlargement must wrap without clipping the service name.
   page.add_style_tag(content=':root{font-size:30px}.brand h1{font-size:2rem}')
   assert page.locator('#page-heading').evaluate('(e)=>e.scrollWidth<=e.clientWidth && e.getBoundingClientRect().right<=innerWidth')
   assert not external,external
   ctx.close()
  ctx=browser.new_context(viewport={'width':320,'height':900});ctx.route('**/*.woff2',lambda r:r.abort());p=ctx.new_page();p.goto(base);p.evaluate('document.fonts.ready');expect(p.locator('#page-heading')).to_be_visible();assert p.locator('#page-heading').evaluate('(e)=>e.scrollWidth<=e.clientWidth');p.screenshot(path=str(OUT/f'fallback-{kind}-320.png'));ctx.close()
 # Compare original and new header using the actual previous markup at equal viewport.
 old=Path('/tmp/mla-logo-work/before.html')
 if old.exists():
  for width in [390,1280]:
   ctx=browser.new_context(viewport={'width':width,'height':900});p=ctx.new_page();ctx.route(base,lambda r:r.fulfill(body=old.read_text(),content_type='text/html'));p.goto(base);p.locator('.brand').screenshot(path=str(OUT/f'before-{width}.png'));ctx.close()
 p=browser.new_page(viewport={'width':400,'height':460});svg=re.search(r'<span data-brand-symbol="B-3">(.*?)</span>',(ROOT/'index.html').read_text(),re.S)[1];p.set_content('<style>body{margin:0;background:#11151b;color:#f0f1f3}svg{display:block;width:auto;height:300px}</style>'+svg);p.locator('svg').screenshot(path=str(OUT/'svg-symbol.png'))
 browser.close()
for s in servers:s.shutdown()
(OUT/'metrics.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print('PASS 24 width/language/source-dist cases; custom font, fallback, 200%+ text, navigation, no external requests, unchanged archive/photo data (language settings intentionally persist)')

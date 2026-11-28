"""Temporary Preview logo comparison: real pointer/keyboard, isolated synthetic data only."""
import functools,json,re,threading,subprocess,hashlib
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright,expect
from static_distribution import SNAPSHOT
from data_preservation import seed_data
from brand_text_metrics import SPECS,measure,check
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brand-logo-02-round6';OUT.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
records=[];servers=[]
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 for kind in ['source','dist']:
  root=ROOT/'dist' if kind=='dist' else ROOT
  s=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)));servers.append(s);threading.Thread(target=s.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{s.server_port}/'
  for width in [320,375,390,393,430,1280]:
   c=b.new_context(viewport={'width':width,'height':852},is_mobile=width<600,has_touch=width<600);external=[];c.route('https://**/*',lambda r:(external.append(r.request.url),r.abort()))
   p=c.new_page();p.goto(base+'?logo-compare=1');p.evaluate('MLAReady');p.evaluate('document.fonts.ready')
   for lang in ['ja','en']:
    p.locator('#ui-language').select_option(lang);expect(p.locator('#ui-language')).to_be_enabled()
    positions=[]
    expect(p.locator('.brand-comparison button[aria-pressed="true"]')).to_have_count(1)
    controls=p.locator('.brand-comparison button').evaluate_all('(nodes)=>nodes.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}})')
    assert len(controls)==6 and all(r['w']>=44 and r['h']>=44 and r['x']>=0 and r['right']<=width for r in controls),controls
    for i,r in enumerate(controls):
     for q in controls[i+1:]:assert r['right']<=q['x']+.1 or q['right']<=r['x']+.1 or r['bottom']<=q['y']+.1 or q['bottom']<=r['y']+.1
    for name in list(SPECS):
     button=p.locator('.brand-comparison button').filter(has_text=re.compile('^'+re.escape(name)+'$'));button.tap() if width<600 else button.click()
     expect(button).to_have_attribute('aria-pressed','true')
     info=measure(p);check(info,name)
     positions.append((tuple(info['brand']),info['sections'][1]))
     if kind=='source':
      p.locator('.brand').screenshot(path=str(OUT/f'header-{width}-{lang}-{name}.png'))
      if width in [320,393,1280]:p.screenshot(path=str(OUT/f'top-{width}-{lang}-{name}.png'))
     records.append({'kind':kind,'viewportWidth':width,'lang':lang,'variant':name,**info})
    assert len(set(positions))==1,positions
   p.add_style_tag(content=':root{font-size:30px}')
   for name in SPECS:
    p.locator('.brand-comparison button').filter(has_text=re.compile('^'+name+'$')).click()
    check(measure(p),name,2)
   assert not external; c.close()
  # Opt-in only; production/GitHub hostnames must never show the temporary panel.
  for host,optin,enabled in [('127.0.0.1',False,False),('deploy-preview.my-listening-archive.pages.dev',True,True),('6b371f4b.my-listening-archive.pages.dev',True,True),('my-listening-archive.pages.dev',True,False),('kochitaro.github.io',True,False)]:
   c=b.new_context();c.route('https://**/*',lambda r:r.abort());p=c.new_page()
   if host=='127.0.0.1':p.goto(base)
   else:
    url='http://'+host+'/'
    c.route(url+'**',lambda r:r.fulfill(body=(root/'index.html').read_text(),content_type='text/html') if r.request.resource_type=='document' else r.fulfill(body=(root/'brand-compare.js').read_text(),content_type='text/javascript') if 'brand-compare.js' in r.request.url else r.abort());p.goto(url+'?logo-compare=1')
   assert p.locator('.brand-comparison').count()==int(enabled),(kind,host)
   if host=='127.0.0.1':
    check(measure(p),'T-5')
   c.close()
 # Synthetic state retention in actual search/archive/Insights, with read/write instrumentation.
 c=b.new_context(viewport={'width':393,'height':852},is_mobile=True,has_touch=True);p=c.new_page();c.route('https://**/*',lambda r:r.abort());p.goto(base+'?logo-compare=1');p.evaluate('MLAReady');p.on('dialog',lambda d:d.accept())
 seed=seed_data();seed['listening']=[dict(seed['listening'][0],entryId='synthetic-'+str(i),title='Synthetic album '+str(i)) for i in range(35)]
 with p.expect_event('dialog'):
  p.locator('#import-json').set_input_files({'name':'synthetic.json','mimeType':'application/json','buffer':json.dumps(seed).encode()})
 expect(p.locator('#ui-language')).to_be_enabled()
 p.locator('[data-section=listening]').click()
 # Title search has a single local mock response.
 c.route('https://musicbrainz.org/**',lambda r:r.fulfill(json={'count':1,'release-group-count':1,'release-groups':[{'id':'synthetic-work','title':'Synthetic search result','primary-type':'Album','artist-credit':[{'name':'Synthetic artist'}]}]}))
 p.locator('[data-search-mode=title]').click();p.locator('#query').fill('Synthetic search');p.locator('#search-btn').click();expect(p.locator('#results .result')).to_have_count(1,timeout=30000)
 p.evaluate('''()=>{window.logoReads=0;window.logoWrites=0;window.logoStorageWrites=0;window.logoMutations=0;window.logoRequests=0;const tx=IDBDatabase.prototype.transaction;IDBDatabase.prototype.transaction=function(...a){if(a[1]==='readwrite')logoWrites++;else logoReads++;return tx.apply(this,a)};for(const k of ['setItem','removeItem','clear']){const fn=Storage.prototype[k];Storage.prototype[k]=function(...a){logoStorageWrites++;return fn.apply(this,a)}};const f=window.fetch;window.fetch=function(...a){logoRequests++;return f.apply(this,a)}}''')
 for screen in ['archive','insights','archive-large','insights-large']:
  if screen in ['insights','insights-large']:p.locator('#insights-screen').click()
  elif screen=='archive-large':
   p.locator('#archive-screen').click();p.add_style_tag(content=':root{font-size:30px}')
  else:p.locator('#filters-toggle').click()
  expect(p.locator('#ui-language')).to_be_enabled();p.wait_for_timeout(200)
  p.evaluate("window.scrollTo({top:400,behavior:'instant'})");p.wait_for_timeout(100)
  before=p.evaluate(SNAPSHOT)
  panel_state=p.locator('#filters-wrap').get_attribute('class')
  p.evaluate('''()=>{window.logoOriginalNodes=[document.querySelector('#library').firstChild,document.querySelector('#results').firstChild,document.querySelector('#listening-insights').firstChild];window.logoReads=window.logoWrites=window.logoStorageWrites=window.logoRequests=window.logoMutations=0;window.logoObserver=new MutationObserver(m=>logoMutations+=m.length);for(const id of ['library','results','listening-insights'])logoObserver.observe(document.getElementById(id),{childList:true,subtree:true,attributes:true});window.logoY=scrollY}''')
  for name in list(SPECS)+['T-5']:
   p.locator('.brand-comparison button').filter(has_text=re.compile('^'+re.escape(name)+'$')).tap()
   assert p.evaluate('scrollY===logoY'),(screen,name)
  # Keyboard activation is also local and must not scroll.
  btn=p.locator('.brand-comparison button').filter(has_text='T-1');btn.evaluate('(e)=>e.focus({preventScroll:true})');btn.press('Space')
  counters=p.evaluate('''()=>({reads:logoReads,writes:logoWrites,storage:logoStorageWrites,requests:logoRequests,mutations:logoMutations,nodes:logoOriginalNodes.every((n,i)=>n===[document.querySelector('#library').firstChild,document.querySelector('#results').firstChild,document.querySelector('#listening-insights').firstChild][i]),y:scrollY===logoY})''')
  assert counters==dict(reads=0,writes=0,storage=0,requests=0,mutations=0,nodes=True,y=True),counters
  assert p.locator('#filters-wrap').get_attribute('class')==panel_state
  assert p.evaluate(SNAPSHOT)==before;expect(p.locator('#results .result')).to_have_count(1);assert p.locator('#query').input_value()=='Synthetic search'
  p.evaluate('logoObserver.disconnect()')
  p.locator('.brand-comparison button').filter(has_text='T-5').tap()
  if screen=='archive':p.locator('#filters-toggle').click()
  p.evaluate("document.activeElement?.blur();scrollTo({top:0,behavior:'instant'})");p.wait_for_function('scrollY===0');p.screenshot(path=str(OUT/f'T5-{screen}-393.png'))
  print('PASS state retention',screen,counters,flush=True)
 p.reload();p.evaluate('document.fonts.ready');check(measure(p),'T-5');c.close()
 # Archive the exact original geometry without shipping it in the app.
 previous=subprocess.check_output(['git','show','294ee4c:index.html'],cwd=ROOT,text=True)
 for name in ['B-4','F-1','F-2','F-3']:
  original=re.search(r'<span data-brand-symbol="'+name+r'">(.*?)</span>',previous,re.S)[1]
  asset=ROOT/('docs/brand-symbols/archive' if name=='B-4' else 'docs/brand-symbols/f-series')/(name+'.svg')
  assert asset.read_text()==original
  assert original not in (ROOT/'index.html').read_text()
 raw=ROOT/'docs/brand-symbols/f-series/F-1-reference.jpg'
 assert hashlib.sha256(raw.read_bytes()).hexdigest()=='373e88dba8c639f3f329761f2bb59c7efa4985b583fd6f4306028d9e22a84651'
 assert len(list((ROOT/'dist').iterdir()))==21
 assert not (ROOT/'dist/docs').exists()
 assert 'data-brand-symbol' not in (ROOT/'dist/index.html').read_text()
 b.close()
for s in servers:s.shutdown()
(OUT/'metrics.json').write_text(json.dumps(records,indent=2));print('PASS 144 wordmark cases, 200% text, no symbol/slot, stable 40px header and following UI, archived original SVGs, preview opt-in, default T-5')

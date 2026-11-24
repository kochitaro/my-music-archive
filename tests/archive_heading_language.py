"""Focused visual/semantic checks, synthetic records, intercepted external traffic."""
import json, os, subprocess, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album

OUT=ROOT/'docs/archive-heading-language'
OUT.mkdir(exist_ok=True)
seed=dict(version=3,listening=[album(f'Listening {i}') for i in range(12)],collection=[album('Collection')],live=[dict(entryId='show',title='Live show',date='2026-01-02',venue='Tokyo')])
base=subprocess.check_output(['git','show','1eedc61:index.html'],text=True)
server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/'

def metrics(p):
 return p.evaluate('''()=>{const box=s=>{const r=document.querySelector(s).getBoundingClientRect();return {y:r.y,w:r.width,h:r.height}};return {year:box('#library h3'),card:box('#library .coverbtn'),search:box('#search-panel')}}''')

with sync_playwright() as pw:
 for engine in ['chromium','webkit']:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if engine=='chromium' else pw.webkit.launch(executable_path=os.environ.get('MLA_WEBKIT'))
  for width in [390,1280]:
   def context():
    c=b.new_context(viewport=dict(width=width,height=844),has_touch=width==390,is_mobile=width==390)
    c.route('https://**/*',lambda r:r.abort())
    c.add_init_script('if(!localStorage.getItem('+json.dumps(KEY)+'))localStorage.setItem('+json.dumps(KEY)+','+json.dumps(json.dumps(seed))+')')
    return c
   old=context();q=old.new_page();q.route(url,lambda r:r.fulfill(body=base,content_type='text/html'));q.goto(url);q.wait_for_function('!document.querySelector("main").inert')
   before={}
   for lang in ['ja','en']:
    q.locator('#ui-language').select_option(lang)
    for area in ['listening','collection','live']:
     q.locator(f'[data-section={area}]').click();q.evaluate('scrollTo(0,0)');before[lang,area]=metrics(q)
   old.close()
   c=context();p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(url);p.wait_for_function('!document.querySelector("main").inert')
   for lang in ['ja','en']:
    p.locator('#ui-language').select_option(lang);assert p.locator('html').get_attribute('lang')==lang
    for area in ['listening','collection','live']:
     p.locator(f'[data-section={area}]').click();p.evaluate('scrollTo(0,0)')
     heading=p.locator('.archive-heading');assert heading.evaluate('e=>getComputedStyle(e).position')=='absolute'
     assert heading.bounding_box()['height']==1
     assert p.locator('#count').evaluate('e=>getComputedStyle(e).display')=='none'
     expect(p.locator('#archive-panel')).to_have_attribute('aria-labelledby','library-title')
     title=p.locator('#library-title').inner_text();assert title in ['Listening','Collection','Live','リスニング','購入','ライブ']
     assert f'heading "{title}' in p.locator('#archive-panel').aria_snapshot()
     refs=p.locator('[aria-labelledby]').evaluate_all('els=>els.flatMap(e=>e.getAttribute("aria-labelledby").split(/\\s+/).filter(id=>!document.getElementById(id)))');assert not refs,refs
     now=metrics(p);prior=before[lang,area];gain=prior['year']['y']-now['year']['y'];assert gain>=20,(gain,engine,area)
     assert now['card']['w']==prior['card']['w'] and now['card']['h']==prior['card']['h']
     if area!='live':assert now['search']==prior['search']
     expect(p.locator('#library h3').first).to_be_visible();expect(p.locator('#display-options')).to_be_visible()
     p.locator('#display-options').click();expect(p.locator('#display-modal')).to_have_class('modal open');p.locator('#display-close').click()
     p.locator('#insights-screen').click();expect(p.locator('#archive-toolbar')).to_be_hidden();p.locator('#archive-screen').click()
     if width==390:p.screenshot(path=str(OUT/f'{engine}-{width}-{lang}-{area}.png'))
     print('PASS',engine,width,lang,area,'year moved up',round(gain,2),'px; card/search unchanged; label references, year options, insights',flush=True)
    p.wait_for_timeout(300);p.evaluate('scrollTo(0,document.body.scrollHeight)');p.wait_for_timeout(100)
    s=p.locator('#ui-language');style=s.evaluate('e=>{const s=getComputedStyle(e);return [s.textAlign,s.textAlignLast,s.paddingLeft,s.paddingRight,s.appearance,s.backgroundImage]}')
    assert style[:2]==['center','center'] and style[2]==style[3] and style[4]=='none' and 'svg' in style[5]
    assert p.locator('#sort').evaluate('e=>getComputedStyle(e).textAlignLast')!='center'
    if width==390:p.screenshot(path=str(OUT/f'{engine}-{width}-{lang}-language.png'))
    assert s.bounding_box()['y']+s.bounding_box()['height']<=p.locator('#archive-toolbar').bounding_box()['y']
   p.reload();p.wait_for_function('!document.querySelector("main").inert');assert p.locator('#ui-language').input_value()=='en'
   # Manual registration and IDB persistence for both album areas.
   for area in ['listening','collection']:
    p.locator(f'[data-section={area}]').click();p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Manual '+area);p.locator('#manual-artist').fill('Synthetic Artist');p.locator('#save').click();expect(p.locator('#modal')).not_to_have_class('modal open')
    expect(p.get_by_text('Manual '+area,exact=True)).to_be_visible()
   p.reload();p.wait_for_function('!document.querySelector("main").inert')
   for area in ['listening','collection']:
    p.locator(f'[data-section={area}]').click();expect(p.get_by_text('Manual '+area,exact=True)).to_be_visible()
   assert not errors,errors
   print('PASS',engine,width,'language CSS scope / footer / reload persistence / manual add and IDB persistence / no JS errors',flush=True)
   c.close()
  b.close()
server.shutdown()

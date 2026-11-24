"""Touch control font/geometry regression, Chromium + WebKit; no real iPhone claim.
Run: python tests/ios_input_zoom.py (PLAYWRIGHT_BROWSERS_PATH if needed).
Uses synthetic data and a fresh browser context for each comparison.
"""
import json, os, subprocess, threading
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album, edit
from http.server import ThreadingHTTPServer

SEED = dict(version=3, listening=[album('Album', genre='Ambient', tags=['Night'])],
            collection=[album('Purchase', store='Shop', format='LP', condition='Used')],
            live=[dict(entryId='show', title='Show', venue='Tokyo', date='2026-01-02', artists=['Artist'], memo='Notes')])
CONTROL = 'input,textarea,select'
SNAPSHOT = '''els=>els.filter(e=>e.getClientRects().length).map(e=>{
 const s=getComputedStyle(e),r=e.getBoundingClientRect();return {
 key:e.id.replace(/^live-artist-[0-9]+$/,'live-artist')||e.closest('[id]')?.id+':'+e.getAttribute('aria-label'),type:e.type,
 font:parseFloat(s.fontSize),width:r.width,height:r.height,
 padding:s.padding,line:s.lineHeight}})'''


def run(browser, url, source, width, touch, standalone, language, fixed):
 ctx=browser.new_context(viewport=dict(width=width,height=844),is_mobile=touch,has_touch=touch)
 ctx.route('https://**/*', lambda r:r.abort())
 ctx.route(url, lambda r:r.fulfill(body=source,content_type='text/html'))
 ctx.add_init_script('localStorage.setItem('+json.dumps(KEY)+','+json.dumps(json.dumps(SEED))+');localStorage.setItem("mma-ui-language",'+json.dumps(language)+');'+
                     ('Object.defineProperty(navigator,"standalone",{value:true});' if standalone else ''))
 p=ctx.new_page();p.set_default_timeout(8000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 p.goto(url);p.evaluate('MLAReady')
 result={};audit={}
 def check(scene):
  rows=p.locator(CONTROL).evaluate_all(SNAPSHOT);result[scene]=rows
  result[scene+'-text']=p.locator('h1,h2,h3,label,.tile .title,.tile .small').evaluate_all('els=>els.filter(e=>e.getClientRects().length).map(e=>({key:e.id||e.textContent,font:getComputedStyle(e).fontSize}))')
  audit[scene]=p.locator(CONTROL).evaluate_all('els=>els.map(e=>({id:e.id,type:e.type,font:getComputedStyle(e).fontSize,visible:!!e.getClientRects().length}))')
  if fixed and touch:
   assert all(r['font']>=16 for r in rows if r['type'] not in ['file','checkbox']), (scene,rows)
  assert p.evaluate('document.documentElement.scrollWidth<=innerWidth'),scene
  for element in p.locator(CONTROL).all() if fixed else []:
   if not element.is_visible() or not element.is_enabled() or element.get_attribute('type') in ['file','checkbox','hidden']:continue
   element.focus();expect(element).to_be_focused()
   if fixed and width==390 and element.get_attribute('id') in ['genre','tags','live-title','e-live-title']:
    p.screenshot(path=str(ROOT/'docs/ios-input-zoom'/f'{browser.browser_type.name}-{scene}-{element.get_attribute("id")}-focus.png'))
   if element.evaluate('e=>e.matches("textarea,input:not([type=date])")'):
    old=element.input_value();element.fill('2026' if element.get_attribute('inputmode')=='numeric' else '17' if element.get_attribute('type')=='number' else '日本語 Test');element.fill(old)
   assert p.evaluate('visualViewport.scale')==1
  dialog=p.locator('.modal.open .dialog')
  if dialog.count():assert dialog.evaluate('e=>e.scrollWidth<=e.clientWidth+1'),scene
 def close(selector):
  p.locator(selector).click();assert p.evaluate('visualViewport.scale')==1
 for area,title in [('listening','Album'),('collection','Purchase'),('live','Show')]:
  p.locator(f'[data-section={area}]').click();check(area+'-archive')
  p.locator('#sort-toggle').click();check(area+'-sort')
  p.locator('#filters-toggle').click();check(area+'-filter');p.locator('#filters-toggle').click()
  p.locator('#display-options').click();check(area+'-display');p.locator('#display-close').click()
  edit(p,title);check(area+'-edit')
  if fixed:
   p.locator('#memo').fill('Regression note');p.locator('#save').click();expect(p.locator('#modal')).not_to_have_class('modal open')
   edit(p,title);expect(p.locator('#memo')).to_have_value('Regression note')
  close('#close')
  p.locator('#add-live-trigger' if area=='live' else '#manual-add-trigger').click();check(area+'-create')
  if area=='live':
   p.locator('#live-artists .btn').click();check('live-extra-artist');close('#close-live-create')
  else:close('#close')
 assert not errors,errors
 ctx.close();return result,audit


def main():
 baseline=subprocess.check_output(['git','show',os.environ.get('MLA_BASE','cd55fcb')+':index.html'],cwd=ROOT).decode()
 fixed=(ROOT/'index.html').read_text()
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
 url=f'http://127.0.0.1:{server.server_port}/'
 evidence=ROOT/'docs/ios-input-zoom';evidence.mkdir(exist_ok=True)
 audit={}
 with sync_playwright() as pw:
  for engine in os.environ.get('MLA_ENGINES','chromium,webkit').split(','):
   b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if engine=='chromium' else pw.webkit.launch()
   for width,touch,standalone,language in [(390,True,False,'en'),(320,True,True,'ja'),(375,True,False,'ja'),(430,True,True,'en'),(844,True,True,'en'),(1030,False,False,'en')]:
    before,ba=run(b,url,baseline,width,touch,standalone,language,False)
    after,aa=run(b,url,fixed,width,touch,standalone,language,True)
    for scene,rows in before.items():
     if scene.endswith('-text'):
      assert rows==after[scene],(engine,width,scene);continue
     for old,new in zip(rows,after[scene],strict=True):
      assert abs(old['width']-new['width'])<=1 and abs(old['height']-new['height'])<=1,(engine,width,scene,old,new)
      if not touch:assert old==new,(old,new)
    key=f'{engine}-{width}-{language}-standalone-{standalone}'
    audit[key]=dict(before=ba,after=aa,geometry_before=before,geometry_after=after)
    print('PASS',key,'fonts, focus/input/close, geometry, containment, edit/save',flush=True)
   b.close()
 (evidence/('audit-'+os.environ.get('MLA_ENGINES','all')+'.json')).write_text(json.dumps(audit,ensure_ascii=False,separators=(',',':'))+'\n')
 server.shutdown()

if __name__=='__main__':main()

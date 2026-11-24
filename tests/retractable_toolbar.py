"""UI regressions: isolated synthetic archives, no external traffic or iPhone claim."""
import json, os, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album
from mobile_navigation import TOUCH
OUT=ROOT/'docs/retractable-toolbar';OUT.mkdir(exist_ok=True)
seed=dict(version=3,listening=[album('Album '+str(i),genre='Ambient') for i in range(36)],collection=[album('Purchase',store='Shop')],live=[dict(entryId='show',title='Show',venue='Tokyo',date='2026-01-02')])
server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/'
with sync_playwright() as pw:
 for engine in ['chromium','webkit']:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if engine=='chromium' else pw.webkit.launch(executable_path=os.environ.get('MLA_WEBKIT'))
  for width in [390,1280]:
   c=b.new_context(viewport=dict(width=width,height=844),is_mobile=width==390,has_touch=width==390)
   c.route('https://**/*',lambda r:r.abort());c.add_init_script('if(!localStorage.getItem('+json.dumps(KEY)+'))localStorage.setItem('+json.dumps(KEY)+','+json.dumps(json.dumps(seed))+')')
   p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(url);p.wait_for_function('!document.querySelector("main").inert')
   p.evaluate('''()=>{window.selectFocus=[];const original=HTMLElement.prototype.focus;HTMLElement.prototype.focus=function(...args){if(this.tagName==='SELECT')selectFocus.push(this.id);return original.apply(this,args)}}''')
   bar=p.locator('#archive-toolbar');handle=p.locator('#archive-toolbar-handle');panels=p.locator('#archive-toolbar-panels')
   def settle():p.wait_for_timeout(260)
   def padding():return p.evaluate('parseFloat(getComputedStyle(document.body).paddingBottom)')
   def shot(name):p.screenshot(path=str(OUT/f'{engine}-{width}-{lang}-{name}.png'))
   for lang in ['ja','en']:
    p.locator('#ui-language').select_option(lang);p.evaluate('scrollTo(0,0)');settle()
    assert p.locator('.langbar').count()==1
    assert p.locator('.langbar').evaluate('e=>!!(document.querySelector("footer").compareDocumentPosition(e)&Node.DOCUMENT_POSITION_FOLLOWING)')
    assert p.locator('#sections').bounding_box()['y']<p.locator('.brand').bounding_box()['y']+p.locator('.brand').bounding_box()['height']+30
    normal=padding();shot('expanded')
    handle.click();settle();expect(handle).to_have_attribute('aria-expanded','false');expect(p.locator('#archive-view-toggle')).to_be_hidden()
    compact=padding();assert compact<normal-30,(compact,normal)
    assert abs(bar.bounding_box()['height']-compact)<1;shot('collapsed')
    assert p.locator('#archive-toolbar-actions').evaluate('e=>e.inert')
    handle.focus();handle.press('Enter');settle();expect(handle).to_have_attribute('aria-expanded','true');assert abs(padding()-normal)<1
    handle.press('Space');settle();expect(handle).to_have_attribute('aria-expanded','false');handle.click();settle()
    # Pointer sequences stay entirely on the handle; no archive gesture hooks are added.
    def swipe_handle(dy,dx=0):
     box=handle.bounding_box();x=box['x']+box['width']/2;y=box['y']+box['height']/2
     p.mouse.move(x,y);p.mouse.down();p.mouse.move(x+dx,y+dy,steps=5);p.mouse.up();settle()
    swipe_handle(30);expect(handle).to_have_attribute('aria-expanded','false')
    swipe_handle(-40);expect(handle).to_have_attribute('aria-expanded','true')
    swipe_handle(0,60);expect(handle).to_have_attribute('aria-expanded','true')
    for area in ['listening','collection','live']:
     p.locator(f'[data-section={area}]').click()
     assert p.locator('.archive-toolbar-inner > button:visible').count()==(4 if area=='live' else 3)
     for i in range(3):
      p.evaluate('selectFocus=[]');p.locator('#sort-toggle').click();expect(panels).to_be_visible();assert p.evaluate('selectFocus')==[]
      if i==0:shot(area+'-sort')
      p.locator('#sort').select_option('date-asc');p.locator('#group').select_option('none')
      p.locator('#filters-toggle').click();expect(p.locator('#sort-wrap')).to_be_hidden();expect(p.locator('#filters-wrap')).to_be_visible()
      fid='genre-filter' if area=='listening' else 'store-filter' if area=='collection' else 'venue-filter'
      value='Ambient' if area=='listening' else 'Shop' if area=='collection' else 'Tokyo'
      p.locator('#'+fid).select_option(value)
      if i==0:p.locator('.toolbar-panel-close').click()
      elif i==1:p.locator('.brand').click()
      else:p.keyboard.press('Escape')
      expect(panels).to_be_hidden();settle();assert abs(bar.bounding_box()['height']-normal)<1
      assert p.locator('#sort').input_value()=='date-asc';assert p.locator('#'+fid).input_value()==value
     # Reproduce an inner-only close (the former stale outer container failure).
     p.locator('#sort-toggle').click();p.locator('#sort-wrap').evaluate('e=>e.classList.add("hidden")');expect(panels).to_be_hidden()
     p.locator('#sort-toggle').click();p.locator('.toolbar-panel-close').click()
     p.locator('#sort-toggle').focus();p.keyboard.press('Enter');expect(p.locator('.toolbar-panel-close')).to_be_focused();p.keyboard.press('Tab');expect(p.locator('#sort')).to_be_focused();p.keyboard.press('Escape');expect(panels).to_be_hidden()
     p.locator('#insights-screen').click();expect(bar).to_be_hidden();assert padding()==0;p.locator('#archive-screen').click()
     p.locator('#add-live-trigger' if area=='live' else '#manual-add-trigger').click();expect(bar).to_be_hidden();assert padding()==0;p.locator('#close-live-create' if area=='live' else '#close').click();expect(bar).to_be_visible()
    p.locator('[data-section=listening]').click();p.evaluate('scrollTo(0,600)');settle()
    for collapse in [False,True]:
     if collapse:handle.click();settle()
     p.evaluate('scrollBy(0,3)');settle();top=p.locator('#back-to-top');expect(top).to_be_visible()
     assert top.bounding_box()['y']+top.bounding_box()['height']<=bar.bounding_box()['y']
    handle.click();settle();p.evaluate('scrollTo(0,document.body.scrollHeight)');settle()
    assert p.locator('.langbar').bounding_box()['y']+p.locator('.langbar').bounding_box()['height']<=bar.bounding_box()['y']
    p.evaluate('scrollTo(0,0)')
   if width==390:
    p.evaluate(TOUCH,dict(selector='#library-title',points=[[280,300],[200,301],[100,302]]));expect(p.locator('[data-section=collection]')).to_have_class('tab active');p.wait_for_timeout(720)
    p.evaluate(TOUCH,dict(selector='#library-title',points=[[200,300],[201,380],[202,470]]));expect(p.locator('[data-section=collection]')).to_have_class('tab active')
   p.emulate_media(reduced_motion='reduce');assert handle.evaluate('e=>getComputedStyle(e).transitionDuration')=='0s'
   p.reload();p.wait_for_function('!document.querySelector("main").inert');assert p.locator('#ui-language').input_value()=='en'
   assert not errors,errors
   print('PASS',engine,width,'ja/en collapse padding tap keyboard handle-swipe panel-repeat inner-close select-focus language modal insights top footer gestures reduced-motion',flush=True)
   c.close()
  b.close()
server.shutdown()

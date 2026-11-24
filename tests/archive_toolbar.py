"""Archive toolbar regression. Fresh profiles, synthetic data, blocked external traffic.
Run python tests/archive_toolbar.py; MLA_WEBKIT may select a local WebKit bundle.
"""
import json, os, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album
from mobile_navigation import TOUCH

OUT=ROOT/'docs/archive-toolbar';OUT.mkdir(exist_ok=True)
seed=dict(version=3,listening=[album('Album '+str(i),genre='Ambient',tags=['Night']) for i in range(36)],collection=[album('Purchase',store='Shop',format='LP')],live=[dict(entryId='show',title='Show',venue='Tokyo',date='2026-01-02',artists=['Artist'])])
server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/'
with sync_playwright() as pw:
 for engine in ['chromium','webkit']:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if engine=='chromium' else pw.webkit.launch(executable_path=os.environ.get('MLA_WEBKIT'))
  for width in [390,1280]:
   ctx=browser.new_context(viewport=dict(width=width,height=844),has_touch=width==390,is_mobile=width==390)
   ctx.route('https://**/*',lambda r:r.abort())
   ctx.add_init_script('if(!localStorage.getItem('+json.dumps(KEY)+'))localStorage.setItem('+json.dumps(KEY)+','+json.dumps(json.dumps(seed))+')')
   p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(url)
   expect(p.locator('#archive-toolbar')).to_be_visible();p.wait_for_function('!document.querySelector("main").inert')
   for lang in ['ja','en']:
    p.locator('#ui-language').select_option(lang)
    for area in ['listening','collection','live']:
     p.locator(f'[data-section={area}]').click();expect(p.locator('#archive-toolbar')).to_be_visible()
     assert p.locator('#archive-toolbar .archive-toolbar-inner > button:visible').count()==(4 if area=='live' else 3)
     assert p.locator('.archive-heading button').count()==0
     p.locator('#insights-screen').click();expect(p.locator('#archive-toolbar')).to_be_hidden();p.locator('#archive-screen').click()
     p.locator('#archive-view-toggle').click();expect(p.locator('#list-tab')).to_have_attribute('aria-pressed','true')
     p.locator('#archive-view-toggle').click();expect(p.locator('#grid-tab')).to_have_attribute('aria-pressed','true')
     p.locator('#sort-toggle').click();
     if lang=='ja' and width==390:p.screenshot(path=str(OUT/f'{engine}-{area}-sort.png'))
     p.locator('#sort').select_option('date-asc');p.locator('#group').select_option('none');p.keyboard.press('Escape');expect(p.locator('#sort-toggle')).to_be_focused()
     p.locator('#filters-toggle').click();fid='venue-filter' if area=='live' else 'store-filter' if area=='collection' else 'genre-filter'
     sel=p.locator('#'+fid);sel.select_option('Tokyo' if area=='live' else 'Shop' if area=='collection' else 'Ambient')
     expect(p.locator('#filters-toggle')).to_have_class('btn ghost has-filter');p.keyboard.press('Escape')
     p.locator('#filters-toggle').click();assert sel.input_value();p.keyboard.press('Escape')
     p.locator('[data-section='+('collection' if area=='listening' else 'listening')+']').click();p.locator(f'[data-section={area}]').click()
     assert p.locator('#sort').input_value()=='date-asc';assert p.locator('#group').input_value()=='none';assert sel.input_value()
     for button in p.locator('#archive-toolbar .archive-toolbar-inner > button:visible').all():
      box=button.bounding_box();assert box['width']>=44 and box['height']>=44
      assert button.evaluate('e=>e.scrollWidth<=e.clientWidth+1')
     assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
     p.screenshot(path=str(OUT/f'{engine}-{width}-{lang}-{area}.png'))
     p.locator('#add-live-trigger' if area=='live' else '#manual-add-trigger').click();expect(p.locator('#archive-toolbar')).to_be_hidden()
     p.locator('#close-live-create' if area=='live' else '#close').click();expect(p.locator('#archive-toolbar')).to_be_visible()
     if area!='live':expect(p.locator('#search-form')).to_be_visible()
   ctx.route('https://musicbrainz.org/**',lambda r:r.fulfill(json={'release-groups':[], 'count':0}))
   for area in ['listening','collection']:
    p.locator(f'[data-section={area}]').click();p.locator('[data-search-mode=title]').click();p.locator('#query').fill('Synthetic missing album');p.locator('#search-btn').click();expect(p.locator('#status')).to_contain_text('No albums found')
   p.locator('[data-section=live]').click();p.locator('#add-live-trigger').click();p.locator('#live-title').fill('Synthetic saved show');p.locator('#live-form button.btn').last.click();expect(p.locator('#live-create-modal')).not_to_have_class('modal open')
   # Clear the venue filter so the newly saved show is visible, then reload to verify IDB.
   p.locator('#filters-toggle').click();p.locator('#venue-filter').select_option('');p.keyboard.press('Escape');expect(p.get_by_text('Synthetic saved show',exact=True)).to_be_visible()
   p.reload();p.wait_for_function('!document.querySelector("main").inert');p.locator('[data-section=live]').click();expect(p.get_by_text('Synthetic saved show',exact=True)).to_be_visible()
   p.locator('[data-section=listening]').click();p.evaluate('scrollTo(0,600)');p.wait_for_timeout(120);expect(p.locator('#back-to-top')).to_be_visible()
   top=p.locator('#back-to-top').bounding_box();bar=p.locator('#archive-toolbar').bounding_box();assert top['y']+top['height']<=bar['y']
   p.wait_for_timeout(3400);expect(p.locator('#back-to-top')).to_be_hidden();p.evaluate('scrollBy(0,20)');p.wait_for_timeout(100);expect(p.locator('#back-to-top')).to_be_visible()
   p.evaluate('scrollTo(0,document.body.scrollHeight)');p.wait_for_timeout(100)
   assert p.locator('footer').evaluate('e=>e.getBoundingClientRect().bottom')<=p.locator('#archive-toolbar').bounding_box()['y']
   # Safe-area CSS formula with a simulated 34px inset (no real iPhone claim).
   p.add_style_tag(content=':root{--archive-bar-height:103px}#archive-toolbar{padding-bottom:34px}')
   assert p.locator('#archive-toolbar').bounding_box()['height']==103
   if width==390:
    p.evaluate('scrollTo(0,0)');p.evaluate(TOUCH,dict(selector='#library-title',points=[[280,300],[200,301],[100,302]]));expect(p.locator('[data-section=collection]')).to_have_class('tab active')
    p.wait_for_timeout(720);p.evaluate(TOUCH,dict(selector='#library-title',points=[[200,300],[201,380],[202,470]]));expect(p.locator('[data-section=collection]')).to_have_class('tab active')
   assert not errors,errors
   print('PASS',engine,width,'3 sections / ja+en / sort+filter retention / modal / Live IDB save / top idle / footer / safe inset / gestures',flush=True)
   ctx.close()
  browser.close()
server.shutdown()

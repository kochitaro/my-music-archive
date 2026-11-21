"""Browser mode installs zero document Pull handlers; test both standalone detectors.
Reload is counted here; pull_refresh.py covers real navigation and busy protection.
All profiles/data are isolated, and mode flags are emulated (NOT iPhone evidence).
"""
import json, os, sys, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, QuietHandler
from pull_refresh import SEND
from mobile_navigation import TOUCH

INIT='''({nav,display})=>{
 window.reloadCount=0;window.pullListeners=[];
 Object.defineProperty(navigator,'standalone',{value:nav,configurable:true});
 const mm=window.matchMedia.bind(window);
 window.matchMedia=q=>q==='(display-mode: standalone)'?{matches:display,media:q,addEventListener(){},removeEventListener(){}}:mm(q);
 const add=EventTarget.prototype.addEventListener;
 EventTarget.prototype.addEventListener=function(type,listener,options){
  if(this===document&&['touchstart','touchmove','touchend','touchcancel'].includes(type))pullListeners.push({type,passive:options?.passive});
  return add.call(this,type,listener,options);
 };
}'''


def run(pw,engine,url):
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if engine=='chromium' else pw.webkit.launch(executable_path=os.environ.get('MLA_WEBKIT'))
 source=(ROOT/'mobile-navigation.js').read_text().replace('location.reload();','window.reloadCount++;')
 for nav,display in [(False,False),(True,False),(False,True),(True,True)]:
  standalone=nav or display
  c=b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
  c.add_init_script('('+INIT+')('+json.dumps(dict(nav=nav,display=display))+')')
  c.route('**/mobile-navigation.js',lambda r:r.fulfill(body=source,content_type='application/javascript'));c.route('https://**/*',lambda r:r.abort())
  p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(url);p.evaluate('MLAReady')
  listeners=p.evaluate('pullListeners')
  assert len(listeners)==(4 if standalone else 0),listeners
  assert all(item['passive'] for item in listeners)
  p.evaluate("()=>{window.pullMutations=[];new MutationObserver(m=>pullMutations.push(...m.map(x=>x.target.id))).observe(document.querySelector('#pull-refresh'),{attributes:true});new MutationObserver(m=>pullMutations.push('status')).observe(document.querySelector('#pull-status'),{childList:true})}")
  for cancelable in [True,False]:
   # Use a fresh load to reset the counted reload's once-only flag.
   if cancelable is False:p.reload();p.evaluate('MLAReady')
   for t,y in [('start',30),('move',80),('move',150)]:
    prevented=p.evaluate(SEND,dict(type='touch'+t,y=y,cancelable=cancelable))
    assert not prevented
   assert p.locator('#pull-refresh').is_visible()==standalone
   assert p.evaluate("getComputedStyle(document.documentElement).overscrollBehaviorY")=='auto'
   assert not p.evaluate("document.documentElement.classList.contains('pull-tracking')")
   p.evaluate('(args)=>{const send='+SEND+';send(args);send(args)}',dict(type='touchend',y=150,cancelable=cancelable))
   assert p.evaluate('reloadCount')==int(standalone)
   expect(p.locator('#pull-refresh')).to_be_hidden()
   if not standalone and cancelable:assert p.evaluate('pullMutations')==[]
  # Both modes keep the archive swipe and top button. Footer remains guarded.
  p.reload();p.evaluate('MLAReady')
  p.evaluate(TOUCH,dict(selector='#library-title',points=[[280,400],[230,400],[160,400],[80,400]]))
  expect(p.locator('[data-section=collection]')).to_have_class('tab active')
  p.wait_for_timeout(750)
  p.add_style_tag(content='.shell{min-height:2400px}')
  p.emulate_media(reduced_motion='reduce');p.evaluate('window.scrollTo(0,700)')
  expect(p.locator('#back-to-top')).to_be_visible();p.locator('#back-to-top').click();p.wait_for_function('scrollY===0')
  p.locator('#page-actions summary').click();p.locator('#reload-page').focus();p.keyboard.press('Enter');assert p.evaluate('reloadCount')==1
  p.reload();p.evaluate('MLAReady');p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Retain input')
  messages=[];p.on('dialog',lambda d:(messages.append(d.message),d.accept()))
  p.locator('#reload-page').evaluate('(el)=>el.click()')
  assert messages and p.evaluate('reloadCount')==0
  expect(p.locator('#manual-title')).to_have_value('Retain input');assert not errors,errors
  print('PASS',engine,'navigator.standalone='+str(nav),'display-mode='+str(display),'document pull handlers='+str(len(listeners)),'native defaults untouched; mode-specific reload, swipe/top/footer protection',flush=True)
  c.close()
 b.close()

if __name__=='__main__':
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
 with sync_playwright() as pw:
  for engine in (sys.argv[1:] or ['chromium','webkit']):run(pw,engine,f'http://127.0.0.1:{server.server_port}/')
 server.shutdown()

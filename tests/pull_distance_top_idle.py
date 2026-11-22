"""180px finger distance versus bounce + real idle/fade/focus behavior.
Isolated standalone flag, not physical iPhone evidence. Only reload is counted;
pull_refresh.py covers actual navigation and IndexedDB/photos.
"""
import os,sys,threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from ui_v0322 import ROOT,QuietHandler
from pull_refresh import SEND


def run(pw,engine,url):
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if engine=='chromium' else pw.webkit.launch(executable_path=os.environ.get('MLA_WEBKIT'))
 c=b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
 c.add_init_script("window.reloadCount=0;Object.defineProperty(navigator,'standalone',{value:true})")
 script=(ROOT/'mobile-navigation.js').read_text().replace('location.reload();','window.reloadCount++;')
 c.route('**/mobile-navigation.js',lambda r:r.fulfill(body=script,content_type='application/javascript'));c.route('https://**/*',lambda r:r.abort())
 p=c.new_page();p.set_default_timeout(8000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 def fresh():p.goto(url);p.evaluate('MLAReady')
 def send(kind,**kwargs):return p.evaluate(SEND,dict(type='touch'+kind,**kwargs))
 for distance,bounce,release in [(96,-250,96),(179,-250,179),(180,-10,180),(220,-20,220),(220,-50,179)]:
  fresh();p.evaluate('(y)=>Object.defineProperty(window,"scrollY",{get:()=>y,configurable:true})',bounce)
  send('start');assert not send('move',y=30+distance,cancelable=False)
  expect(p.locator('#pull-refresh')).to_be_visible() if distance>=180 else expect(p.locator('#pull-refresh')).to_be_hidden()
  if release!=distance:
   send('move',y=30+release,cancelable=False);expect(p.locator('#pull-refresh')).to_be_hidden()
  p.evaluate('(args)=>{const send='+SEND+';send(args);send(args)}',dict(type='touchend',y=30+release))
  assert p.evaluate('reloadCount')==int(release>=180),(distance,bounce,release)
 print('PASS',engine,'finger 96/179/180/220px; bounce -10/-20/-50/-250; retreat below 180; duplicate release reloads once',flush=True)
 fresh();p.add_style_tag(content='.shell{min-height:4000px}')
 p.evaluate("window.idleTrace=[];new MutationObserver(()=>idleTrace.push({time:performance.now(),hidden:document.querySelector('#back-to-top').hidden,idle:document.querySelector('#back-to-top').classList.contains('is-idle'),inert:document.querySelector('#back-to-top').inert,tab:document.querySelector('#back-to-top').tabIndex,pointer:getComputedStyle(document.querySelector('#back-to-top')).pointerEvents,duration:getComputedStyle(document.querySelector('#back-to-top')).transitionDuration})).observe(document.querySelector('#back-to-top'),{attributes:true})")
 top=p.locator('#back-to-top')
 def scroll(y):
  p.evaluate('(y)=>window.scrollTo({top:y,behavior:"instant"})',y)
  p.wait_for_function('(y)=>scrollY===y',arg=y)
  expect(top).to_be_visible() if y>=400 else expect(top).to_be_hidden()
 scroll(399);scroll(400)
 p.wait_for_timeout(2650);expect(top).to_be_visible();assert not top.evaluate('(el)=>el.inert')
 expect(top).to_be_hidden(timeout=1200)
 trace=p.evaluate('idleTrace');fades=[r for r in trace if r['idle'] and not r['hidden']]
 assert fades and all(r['inert'] and r['tab']==-1 and r['pointer']=='none' and r['duration']=='0.18s' for r in fades),trace
 assert top.evaluate('(el)=>el.inert&&el.tabIndex===-1&&el.getAttribute("aria-hidden")==="true"')
 top.evaluate('(el)=>el.focus()');assert not top.evaluate('(el)=>el===document.activeElement')
 # Hit testing: the invisible fixed control must not receive taps.
 assert p.evaluate("document.elementFromPoint(innerWidth-38,innerHeight-38)?.closest('#back-to-top')===null")
 scroll(401);p.wait_for_timeout(1800);scroll(402);p.wait_for_timeout(1700);expect(top).to_be_visible()
 expect(top).to_be_hidden(timeout=1800)
 # Keyboard activity reveals it; focused controls do not disappear mid-use.
 p.locator('#page-actions').evaluate('(el)=>{el.open=true}');p.locator('#page-actions summary').evaluate('(el)=>el.focus({preventScroll:true})')
 p.keyboard.press('Tab');expect(top).to_be_visible();top.focus();p.wait_for_timeout(3300);expect(top).to_be_visible()
 p.locator('#page-heading').evaluate('(el)=>el.focus({preventScroll:true})');expect(top).to_be_hidden(timeout=3600)
 # A native disclosure/button also lets screen reader users request it explicitly.
 p.locator('#page-actions').evaluate('(el)=>{el.open=true}')
 p.locator('#show-top-button').evaluate('(el)=>el.click()')
 expect(top).to_be_visible();expect(top).to_be_focused()
 p.locator('#page-heading').evaluate('(el)=>el.focus({preventScroll:true})')
 p.evaluate("document.querySelector('#view-modal').classList.add('open')");expect(top).to_be_hidden();p.locator('#view-close').focus()
 p.keyboard.press('Tab');expect(top).to_be_hidden();p.evaluate("document.querySelector('#view-modal').classList.remove('open')")
 expect(top).to_be_visible()
 scroll(0);expect(top).to_be_hidden();expect(p.locator('#show-top-button')).to_be_hidden()
 print('PASS',engine,'399/400px; 3s idle fade; new scroll resets timer; hidden hit/focus exclusion; keyboard/footer reveal; focus hold; modal/top hiding',flush=True)
 # Reduced motion removes the fade phase and hides in the idle timer callback.
 p.emulate_media(reduced_motion='reduce');p.evaluate('idleTrace=[]');scroll(700)
 expect(top).to_be_hidden(timeout=3400)
 assert not any(r['idle'] and not r['hidden'] for r in p.evaluate('idleTrace'))
 scroll(701);top.click();p.wait_for_function('scrollY===0');expect(p.locator('#page-heading')).to_be_focused()
 assert not errors,errors
 print('PASS',engine,'reduced-motion immediate idle hide and instant top navigation; page errors 0',flush=True)
 b.close()

if __name__=='__main__':
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
 with sync_playwright() as pw:
  for engine in (sys.argv[1:] or ['chromium','webkit']):run(pw,engine,f'http://127.0.0.1:{server.server_port}/')
 server.shutdown()

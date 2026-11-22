"""Guarded pull refresh: Chromium + WebKit, isolated synthetic photos/data.
Touch sequences verify cancellation/direction/UI. Chromium also sends native CDP touch.
Standalone is set before startup; normal mode has a separate footer test.
Mode flags are emulated, not an iPhone Home Screen run.
"""
import json, os, sys, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, QuietHandler
from data_preservation import seed_data
from mobile_navigation import SEAM, TOUCH

SEND='''({type,x=180,y=30,multi=false,cancelable=true,selector='.shell'})=>{
 const target=document.querySelector(selector),t={identifier:42,clientX:x,clientY:y};
 const e=new Event(type,{bubbles:true,cancelable});
 Object.defineProperties(e,{touches:{value:['touchend','touchcancel'].includes(type)?[]:multi?[t,{...t,identifier:43}]:[t]},changedTouches:{value:[t]}});
 target.dispatchEvent(e);return e.defaultPrevented;
}'''


def run(pw,engine,url,source):
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if engine=='chromium' else pw.webkit.launch(executable_path=os.environ.get('MLA_WEBKIT'))
 c=b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True,accept_downloads=True)
 c.add_init_script("Object.defineProperty(navigator,'standalone',{value:true,configurable:true})")
 original=seed_data()
 c.add_init_script('if(!sessionStorage.seeded){localStorage.setItem("my-music-archive-pilot-v03",JSON.stringify('+json.dumps(original)+'));sessionStorage.seeded="yes"}')
 c.route(url,lambda r:r.fulfill(body=source,content_type='text/html'));c.route('https://**/*',lambda r:r.abort())
 p=c.new_page();p.set_default_timeout(12000);errors=[];dialogs=[];navigations=[]
 p.on('pageerror',lambda e:errors.append(str(e)))
 p.on('dialog',lambda d:(dialogs.append(d.message),d.accept('1') if d.type=='prompt' else d.accept()))
 p.on('framenavigated',lambda f:navigations.append(f.url) if f==p.main_frame else None)
 def ready():p.wait_for_function('window.mobileProbe && !mobileProbe.busy()')
 def send(kind,**kwargs):return p.evaluate(SEND,dict(type='touch'+kind,**kwargs))
 def pull(distance=200,selector='.shell',duplicate=False):
  send('start',selector=selector);send('move',y=50,selector=selector);send('move',y=30+distance,selector=selector)
  if duplicate:p.evaluate('(args)=>{const send='+SEND+';send(args);send(args)}',dict(type='touchend',y=30+distance,selector=selector))
  else:send('end',y=30+distance,selector=selector)
 def data():return p.evaluate('mobileProbe.data()')
 def top():p.evaluate('window.scrollTo({top:0,behavior:"instant"})');p.wait_for_function('scrollY===0')
 p.goto(url);ready();assert data()==original
 assert p.locator('.langbar #page-refresh').count()==0
 assert p.evaluate("getComputedStyle(document.documentElement).overscrollBehaviorY")=='auto'
 assert p.evaluate("getComputedStyle(document.body).overscrollBehaviorY")=='auto'
 # Indicator appears only during a deliberate outward pull, arming at 180px.
 before=len(navigations)
 send('start');assert p.evaluate("getComputedStyle(document.documentElement).overscrollBehaviorY")=='auto'
 send('move',y=50);expect(p.locator('#pull-refresh')).to_be_hidden()
 send('move',y=80);expect(p.locator('#pull-refresh')).to_be_hidden()
 send('end',y=80);expect(p.locator('#pull-refresh')).to_be_hidden();assert len(navigations)==before
 send('start');send('move',y=210);expect(p.locator('#pull-refresh')).to_have_attribute('data-ready','true');p.screenshot(path=f'/tmp/mla-pull-stable-{engine}.png')
 # Retreat below threshold before release cancels even if previously armed.
 send('move',y=75);send('end',y=75);assert len(navigations)==before
 with p.expect_navigation():pull(200,duplicate=True)
 ready();assert len(navigations)==before+1;assert data()==original
 expect(p.locator('#pull-refresh')).to_be_hidden()
 print('PASS',engine,'top pull reloads exactly once; photo/data equality; indicator/threshold/retreat cancellation',flush=True)
 # Cancellation, multitouch, noncancelable events, controls, edges, upward/diagonal.
 before=len(navigations)
 for selector in ['#query','#ui-language']:
  pull(selector=selector);expect(p.locator('#pull-refresh')).to_be_hidden()
 for scenario in ['cancel','multi-start','multi-move','horizontal','up','diagonal']:
  send('start',multi=scenario=='multi-start',x=5 if scenario=='edge' else 180)
  if scenario=='horizontal':send('move',x=290,y=35)
  elif scenario=='up':send('move',y=0)
  elif scenario=='diagonal':send('move',x=260,y=80)
  else:send('move',y=180,multi=scenario=='multi-move',cancelable=scenario!='uncancelable')
  send('cancel' if scenario=='cancel' else 'end',y=180)
  expect(p.locator('#pull-refresh')).to_be_hidden()
 assert len(navigations)==before
 p.add_style_tag(content='.shell{min-height:2400px}')
 p.evaluate('window.scrollTo(0,600)');p.wait_for_function('scrollY===600')
 send('start');assert not send('move',y=180);send('end',y=180);assert len(navigations)==before
 top();send('start');assert not send('move',y=0);send('end',y=0)
 # Arriving at top during a gesture begun below the top must not enable refresh.
 p.evaluate('window.scrollTo(0,100)');send('start');top();send('move',y=180);send('end',y=180);assert len(navigations)==before
 print('PASS',engine,'normal scroll, mid-scroll-to-top, controls, edges, multi/cancel/noncancelable excluded',flush=True)
 # Existing horizontal swipe path still owns horizontal gestures on cards.
 p.evaluate(TOUCH,dict(selector='#library .coverbtn .art',points=[[280,400],[230,401],[160,402],[80,403]],click=True))
 expect(p.locator('[data-section=collection]')).to_have_class('tab active');expect(p.locator('.modal.open')).to_have_count(0)
 p.wait_for_timeout(750);p.locator('[data-section=listening]').click();top()
 p.select_option('#ui-language','ja');ready();top()
 send('start');send('move',y=210);expect(p.locator('#pull-status')).to_have_text('指を離して更新');send('cancel')
 p.select_option('#ui-language','en');ready();top();p.wait_for_timeout(750)
 # Editor / failed-save / active save / restore all use the same release-time guard.
 p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Synthetic pull input');p.locator('#manual-artist').fill('Synthetic')
 top();n=len(dialogs);pull();assert len(dialogs)==n+1;assert 'editor' in dialogs[-1].lower()
 expect(p.locator('#manual-title')).to_have_value('Synthetic pull input');assert data()==original
 p.evaluate("mobileProbe.pause('save')");p.locator('#save').tap();p.wait_for_function('window.paused');top()
 n=len(dialogs);pull();assert len(dialogs)==n+1 and 'progress' in dialogs[-1];assert p.evaluate('mobileProbe.busy()')
 p.evaluate('resume()');ready();saved=data();assert saved!=original
 top()
 with p.expect_navigation():pull()
 ready();assert data()==saved
 raw=json.dumps(saved).encode();p.evaluate("mobileProbe.pause('save')")
 p.locator('#import-json').set_input_files(dict(name='synthetic.json',mimeType='application/json',buffer=raw));p.wait_for_function('window.paused');top()
 n=len(dialogs);pull();assert len(dialogs)==n+1 and 'progress' in dialogs[-1]
 p.evaluate('resume()');ready();assert data()==saved
 print('PASS',engine,'editor, actual save/JSON restore refuse with reason and retain input/data; completion reloads',flush=True)
 # Stopped-state raw rescue and verified branch recovery cannot be interrupted.
 divergent=json.loads(json.dumps(original));divergent['live'][0]['memo']='synthetic divergence'
 p.evaluate('(d)=>localStorage.setItem("my-music-archive-pilot-v03",JSON.stringify(d))',divergent);p.reload();ready()
 p.evaluate("mobileProbe.pause('rescue')");p.locator('#recover-source').tap();p.wait_for_function('window.paused');top()
 n=len(dialogs);pull();assert len(dialogs)==n+1 and p.evaluate('mobileProbe.busy()')
 with p.expect_download():p.evaluate('resume()')
 ready();p.evaluate("mobileProbe.pause('recover')")
 p.locator('#import-json').set_input_files([dict(name='current.json',mimeType='application/json',buffer=raw),dict(name='legacy.json',mimeType='application/json',buffer=json.dumps(divergent).encode())]);p.wait_for_function('window.paused');top()
 n=len(dialogs);pull();assert len(dialogs)==n+1 and p.evaluate('mobileProbe.busy()')
 p.evaluate('resume()');ready();assert data()==saved
 # Keyboard / screen reader route is a standard button inside a native disclosure.
 p.locator('#page-actions summary').focus();p.keyboard.press('Enter');expect(p.locator('#reload-page')).to_be_visible()
 p.locator('#reload-page').focus()
 with p.expect_navigation():p.keyboard.press('Enter')
 ready();assert data()==saved;expect(p.locator('#page-actions')).not_to_have_attribute('open','')
 p.add_style_tag(content='.shell{min-height:2400px}');p.emulate_media(reduced_motion='reduce');p.evaluate('window.scrollTo(0,700)');expect(p.locator('#back-to-top')).to_be_visible()
 p.locator('#back-to-top').click();p.wait_for_function('scrollY===0');expect(p.locator('#page-heading')).to_be_focused()
 print('PASS',engine,'raw rescue/verified recovery refusal; accessible reload; back-to-top/focus preserved',flush=True)
 # Standalone mode uses the exact same guarded pull path; emulate display flag only.
 p.evaluate("Object.defineProperty(navigator,'standalone',{value:true,configurable:true})");top()
 with p.expect_navigation():pull()
 ready();assert data()==saved
 if engine=='chromium':
  # Real browser touch, not a DOM-only event sequence, at a noninteractive header.
  session=c.new_cdp_session(p);top()
  with p.expect_navigation():
   for i,y in enumerate([45,65,110,190,225]):
    session.send('Input.dispatchTouchEvent',{'type':'touchStart' if i==0 else 'touchMove','touchPoints':[dict(x=180,y=y)]});p.wait_for_timeout(35)
   session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
  ready();assert data()==saved
  print('PASS chromium native top pull reload; standalone flag emulation (NOT iPhone standalone)',flush=True)
 else:print('PASS webkit standalone flag emulation (NOT iPhone standalone)',flush=True)
 assert not errors,errors
 # Normal browser mode leaves native refresh alone, keeping the guarded footer.
 legacy=b.new_context(viewport={'width':390,'height':844},has_touch=True)
 legacy.route(url,lambda r:r.fulfill(body=source,content_type='text/html'));legacy.route('https://**/*',lambda r:r.abort())
 q=legacy.new_page();q.goto(url);q.evaluate('MLAReady')
 q.evaluate('(args)=>{const send='+SEND+";send({type:'touchstart'});send({type:'touchmove',y:200});send({type:'touchend',y:200})}",{})
 expect(q.locator('#pull-refresh')).to_be_hidden();expect(q.locator('html')).not_to_have_class('pull-tracking')
 q.locator('#page-actions summary').click();q.locator('#reload-page').focus()
 with q.expect_navigation():q.keyboard.press('Enter')
 q.evaluate('MLAReady');legacy.close()
 print('PASS',engine,'normal mode disables custom pull; accessible footer reload works',flush=True)
 b.close()

if __name__=='__main__':
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
 source=(ROOT/'index.html').read_text().replace('const lifecycle=MLAArchive({validate:migrate,stable,legacy:legacyLifecycle,photos:MLAPhotos});','const lifecycle={...MLAArchive({validate:migrate,stable,legacy:legacyLifecycle,photos:MLAPhotos})};').replace("setSection('listening');showStorageState();",SEAM+"setSection('listening');showStorageState();")
 with sync_playwright() as pw:
  for engine in (sys.argv[1:] or ['chromium','webkit']):run(pw,engine,f'http://127.0.0.1:{server.server_port}/',source)
 server.shutdown()

"""Reproduce iOS-like coordinates/event sequences; NOT physical iPhone evidence.
Only location.reload is counted in this file; pull_refresh.py verifies real navigation/photos.
"""
import os, sys, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, QuietHandler
from pull_refresh import SEND


def run(pw,engine,url,characterize=False):
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if engine=='chromium' else pw.webkit.launch(executable_path=os.environ.get('MLA_WEBKIT'))
 js=(ROOT/'mobile-navigation.js').read_text().replace('location.reload();','window.reloadCount++;')
 for standalone in [True]:
  c=b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
  c.add_init_script('window.reloadCount=0;window.simulatedY=0;Object.defineProperty(window,"scrollY",{get:()=>window.simulatedY,configurable:true});Object.defineProperty(navigator,"standalone",{value:'+str(standalone).lower()+',configurable:true})')
  c.route('**/mobile-navigation.js',lambda r:r.fulfill(body=js,content_type='application/javascript'));c.route('https://**/*',lambda r:r.abort())
  p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  def fresh(y=0):p.goto(url);p.evaluate('MLAReady');p.evaluate('(y)=>window.simulatedY=y',y)
  def send(kind,**kwargs):return p.evaluate(SEND,dict(type='touch'+kind,**kwargs))
  cases=[('fractional top',.5,{},{}),('negative bounce',-25,{},{}),('positive drift during pull',0,{'drift':True},{}),('ordinary button start',0,{},dict(selector='#grid-tab')),('vertical start at edge',0,{},dict(x=12)),('small upward jitter then pull',0,{'jitter':True},{})]
  for name,y,scenario,kw in cases:
   fresh(y);send('start',**kw)
   if scenario.get('jitter'):send('move',y=28,**kw)
   send('move',y=80,**kw)
   if scenario.get('drift'):p.evaluate('window.simulatedY=1.25')
   send('move',y=150,**kw)
   ready=p.locator('#pull-refresh').is_visible()
   send('end',y=150,**kw)
   count=p.evaluate('reloadCount')
   print(engine,'standalone' if standalone else 'browser',name,'ready',ready,'reloads',count,flush=True)
   if not characterize:assert ready and count==1,(name,standalone,ready,count)
  fresh(-20);send('start');send('move',y=80,cancelable=False);send('move',y=150,cancelable=False)
  ready=p.locator('#pull-refresh').is_visible();send('end',y=150,cancelable=False);count=p.evaluate('reloadCount')
  print(engine,'standalone' if standalone else 'browser','noncancelable bounce','ready',ready,'reloads',count,flush=True)
  if not characterize:assert count==int(standalone) and ready==standalone
  if not characterize:
   # The icon and release use the same readiness threshold; never a false ready.
   for distance in [35,50,95,96,120]:
    fresh();send('start');send('move',y=30+distance)
    visible=p.locator('#pull-refresh').is_visible();send('end',y=30+distance)
    assert visible==(distance>=96);assert p.evaluate('reloadCount')==int(visible)
   fresh(20);send('start');p.evaluate('window.simulatedY=0');send('move',y=180);send('end',y=180);assert p.evaluate('reloadCount')==0
   for selector in ['#query','#ui-language','#modal .star-rating']:
    fresh();send('start',selector=selector);send('move',y=180,selector=selector);send('end',y=180,selector=selector);assert p.evaluate('reloadCount')==0
   for cancel in ['touchcancel','multi']:
    fresh();send('start');send('move',y=180,multi=cancel=='multi');send('cancel' if cancel=='touchcancel' else 'end',y=180);assert p.evaluate('reloadCount')==0
   fresh();send('start');send('move',y=180)
   p.evaluate('(args)=>{const send='+SEND+';send(args);send(args)}',dict(type='touchend',y=180));assert p.evaluate('reloadCount')==1
   # Standalone observes native motion; the browser mode cancels the owned pull.
   fresh();send('start')
   assert not p.evaluate("document.documentElement.classList.contains('pull-tracking')")
   assert not send('move',y=80)
   send('cancel');expect(p.locator('html')).not_to_have_class('pull-tracking')
   # Positive drift must not destroy a candidate; it can re-arm at the boundary.
   fresh();send('start');send('move',y=80);p.evaluate('window.simulatedY=6');send('move',y=150)
   expect(p.locator('#pull-refresh')).to_be_hidden()
   p.evaluate("window.simulatedY=-10;window.dispatchEvent(new Event('scroll'))")
   expect(p.locator('#pull-refresh')).to_be_visible();send('end',y=150);assert p.evaluate('reloadCount')==1
   # Even a noncancelable standalone pull cannot bypass an unsaved editor.
   if standalone:
    fresh();p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Keep this input')
    messages=[];p.on('dialog',lambda d:(messages.append(d.message),d.accept()))
    send('start');send('move',y=150,cancelable=False);expect(p.locator('#pull-refresh')).to_be_hidden();send('end',y=150,cancelable=False)
    assert messages and p.evaluate('reloadCount')==0
    expect(p.locator('#manual-title')).to_have_value('Keep this input')
   assert not errors,errors
   print('PASS',engine,'standalone' if standalone else 'browser','threshold/readiness parity, mid-scroll, controls, cancel/multi, single reload',flush=True)
  c.close()
 b.close()

if __name__=='__main__':
 characterize='--characterize' in sys.argv
 engines=[x for x in sys.argv[1:] if not x.startswith('--')] or ['chromium','webkit']
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
 with sync_playwright() as pw:
  for engine in engines:run(pw,engine,f'http://127.0.0.1:{server.server_port}/',characterize)
 server.shutdown()

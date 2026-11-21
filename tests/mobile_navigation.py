"""Chromium + WebKit mobile UI regressions; isolated synthetic data, no external requests.
Run from repository root: python -u tests/mobile_navigation.py
TouchEvent sequences exercise recognizer deterministically, not native iOS gestures.
"""
import json, os, sys, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, QuietHandler, edit
from data_preservation import seed_data

SEAM = """
window.mobileProbe={data:()=>db,busy:()=>operationBusy||saving||settingsBusy,
 pause:method=>{window.paused=false;const original=lifecycle[method];lifecycle[method]=async(...args)=>{
 window.paused=true;await new Promise(r=>window.resume=r);lifecycle[method]=original;
 if(window.mobileProbe.failNextSave&&method==='save'){window.mobileProbe.failNextSave=false;throw Error('Synthetic save failure')}
 return original.apply(lifecycle,args)}}};
"""
TOUCH = """({selector,points,multi=false,cancel=false,click=false})=>{
 const target=document.querySelector(selector);let prevented=[];
 function send(type,point,touches){
  const e=new Event(type,{bubbles:true,cancelable:true});
  const t={identifier:42,clientX:point[0],clientY:point[1]};
  Object.defineProperties(e,{touches:{value:touches===0?[]:multi?[t,{...t,identifier:43}]:[t]},changedTouches:{value:[t]}});
  target.dispatchEvent(e);prevented.push(e.defaultPrevented);
 }
 send('touchstart',points[0],1);
 for(const point of points.slice(1))send('touchmove',point,1);
 send(cancel?'touchcancel':'touchend',points.at(-1),0);
 if(click)document.querySelector(selector).dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,detail:1}));
 return prevented;
} """


def run(pw, engine):
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 url=f'http://127.0.0.1:{server.server_port}/'
 source=(ROOT/'index.html').read_text().replace('const lifecycle=MLAArchive({validate:migrate,stable,legacy:legacyLifecycle,photos:MLAPhotos});','const lifecycle={...MLAArchive({validate:migrate,stable,legacy:legacyLifecycle,photos:MLAPhotos})};').replace("setSection('listening');showStorageState();",SEAM+"setSection('listening');showStorageState();")
 b=(pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if engine=='chromium' else pw.webkit.launch(executable_path=os.environ.get('MLA_WEBKIT')))
 c=b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True,accept_downloads=True)
 c.route(url,lambda r:r.fulfill(body=source,content_type='text/html'))
 c.route('https://**/*',lambda r:r.abort())
 p=c.new_page(); errors=[];dialogs=[]
 p.on('pageerror',lambda e:errors.append(str(e)))
 p.on('dialog',lambda d:(dialogs.append(d.message),d.accept('1') if d.type=='prompt' else d.accept()))
 def ready():
  p.wait_for_function('window.mobileProbe && !mobileProbe.busy()')
 def data():return p.evaluate('mobileProbe.data()')
 def section():return p.locator('#sections .active').get_attribute('data-section')
 def swipe(points,selector='#library-title',**kw):
  return p.evaluate(TOUCH,dict(selector=selector,points=points,**kw))
 left=[[280,300],[240,302],[180,303],[100,304]]
 right=list(reversed(left))
 original=seed_data()
 c.add_init_script('if(!sessionStorage.seeded){localStorage.setItem("my-music-archive-pilot-v03", JSON.stringify('+json.dumps(original)+'));sessionStorage.seeded="yes"}')
 p.goto(url);ready();assert data()==original
 with p.expect_navigation():p.locator('#page-refresh').click()
 ready();assert data()==original
 print('PASS',engine,'normal refresh reloads exact migrated IndexedDB data',flush=True)
 for lang,label in [('ja','ページを更新'),('en','Reload page')]:
  p.select_option('#ui-language',lang);ready();expect(p.locator('#page-refresh')).to_have_attribute('aria-label',label)
 # State parity: tab-specific filters retained by the same setSection path.
 p.select_option('#sort','artist-asc',force=True)
 swipe(left);assert section()=='collection'
 p.select_option('#sort','rating-desc',force=True)
 swipe(left);assert section()=='live'
 swipe(left);assert section()=='live'
 swipe(right);assert section()=='collection';expect(p.locator('#sort')).to_have_value('rating-desc')
 swipe(right);assert section()=='listening';expect(p.locator('#sort')).to_have_value('artist-asc')
 swipe(right);assert section()=='listening'
 # Vertical/diagonal, edges, multitouch, cancel, controls, and horizontal containers.
 for points,kw in [([[200,300],[198,330],[80,450]],{}),([[200,300],[210,320],[80,325]],{}),([[5,300],[150,300]],{}),([[385,300],[200,300]],{}),(left,{'multi':True}),(left,{'cancel':True}),(left,{'selector':'#query'}),(left,{'selector':'#grid-tab'})]:
  result=swipe(points,**kw);assert section()=='listening'
  if kw.get('selector') in ['#query','#grid-tab']:assert not any(result)
 p.evaluate("""()=>{const d=document.createElement('div');d.id='horizontal';d.style='overflow-x:auto;width:100px';d.innerHTML='<div id="wide" style="width:500px">wide</div>';document.querySelector('#archive-content').append(d)}""")
 assert not any(swipe(left,selector='#wide'));assert section()=='listening'
 p.evaluate("document.querySelector('#horizontal').remove()")
 # One swipe, multiple move events, suppress following pointer click, preserve keyboard click.
 p.evaluate("()=>{window.tapCount=0;document.querySelector('#library-title').onclick=()=>window.tapCount++}")
 result=swipe(left,click=True);assert section()=='collection';assert p.evaluate('tapCount')==0,(result,p.evaluate('tapCount'))
 p.evaluate("document.querySelector('#library-title').click()") # detail=0
 assert p.evaluate('tapCount')==1
 p.wait_for_timeout(750)
 p.locator('[data-section=listening]').click()
 print('PASS',engine,'bounded swipes, filter parity, exclusions, axis lock, cancel/multitouch and click suppression',flush=True)
 # Long-page layout fixture; seed intentionally contains only two records per section.
 p.add_style_tag(content='.shell{min-height:2400px}')
 # Top control, keyboard and reduced motion.
 p.evaluate("window.scrollTo(0,700)");expect(p.locator('#back-to-top')).to_be_visible()
 p.locator('#back-to-top').focus();p.keyboard.press('Enter')
 p.wait_for_function('scrollY===0');expect(p.locator('#back-to-top')).to_be_hidden();expect(p.locator('#page-refresh')).to_be_focused()
 p.emulate_media(reduced_motion='reduce')
 p.evaluate("window.scrollTo(0,700)");expect(p.locator('#back-to-top')).to_be_visible()
 p.locator('#back-to-top').click();assert p.evaluate('scrollY')==0
 p.emulate_media(reduced_motion='no-preference')
 # Editor guard keeps exact unsaved values; modal blocks top and gestures.
 p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Unsaved mobile');p.locator('#manual-artist').fill('Artist')
 p.evaluate("window.scrollTo(0,700)");expect(p.locator('#back-to-top')).to_be_hidden()
 n=len(dialogs);p.evaluate("document.querySelector('#page-refresh').click()")
 assert len(dialogs)==n+1;expect(p.locator('#manual-title')).to_have_value('Unsaved mobile')
 swipe(left);assert section()=='listening'
 assert not any(swipe(left,selector='#modal .star-rating'))
 # Hold a real save before IndexedDB commit, attempt refresh, then finish unchanged.
 p.evaluate("mobileProbe.pause('save')");p.locator('#save').click();p.wait_for_function('window.paused')
 p.evaluate("document.querySelector('#page-refresh').click()")
 assert p.evaluate('mobileProbe.busy()');p.evaluate('resume()');ready();expect(p.locator('#modal')).not_to_have_class('modal open')
 created=next(x for x in data()['listening'] if x['title']=='Unsaved mobile')
 p.evaluate('window.scrollTo(0,0)')
 with p.expect_navigation():p.locator('#page-refresh').click()
 ready();assert created in data()['listening']
 print('PASS',engine,'smooth/reduced-motion top, focus, modal hiding, unsaved editor and active-save reload protection',flush=True)
 # CRUD and backup roundtrip across all sections using actual UI.
 for area in ['listening','collection','live']:
  p.locator(f'[data-section={area}]').click();title='Mobile '+area
  if area=='live':
   p.locator('#add-live-trigger').click();p.locator('#live-title').fill(title);p.locator('#live-form button').last.click()
  else:
   p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill(title);p.locator('#manual-artist').fill('Artist');p.locator('#save').click()
  ready();assert any(x['title']==title for x in data()[area])
  edit(p,title);p.locator('#memo').fill('edited mobile');p.locator('#save').click();ready()
  assert next(x for x in data()[area] if x['title']==title)['memo']=='edited mobile'
  edit(p,title);p.locator('#delete').click();p.locator('#delete-accept').click();ready()
  assert all(x['title']!=title for x in data()[area])
 expected=data()
 with p.expect_download() as dl:p.locator('#export-json').click()
 raw=open(dl.value.path(),'rb').read();assert json.loads(raw)==expected
 p.evaluate("window.paused=false;mobileProbe.pause('save')")
 p.locator('#import-json').set_input_files(dict(name='backup.json',mimeType='application/json',buffer=raw))
 p.wait_for_function('window.paused');p.evaluate("document.querySelector('#page-refresh').click()")
 assert p.evaluate('mobileProbe.busy()');swipe(left);assert section()=='live'
 p.evaluate('resume()');ready();assert data()==expected
 p.reload();ready();assert data()==expected
 # Divergent legacy branch triggers the production stopped-state recovery flow.
 divergent=json.loads(json.dumps(original));divergent['live'][0]['memo']='divergent branch'
 p.evaluate('(d)=>localStorage.setItem("my-music-archive-pilot-v03",JSON.stringify(d))',divergent)
 p.reload();ready();expect(p.locator('#storage-state')).to_be_visible()
 p.evaluate("window.paused=false;mobileProbe.pause('rescue')")
 p.locator('#recover-source').click();p.wait_for_function('window.paused')
 p.evaluate("document.querySelector('#page-refresh').click()")
 assert p.evaluate('mobileProbe.busy()')
 with p.expect_download():p.evaluate('resume()')
 ready()
 p.evaluate("window.paused=false;mobileProbe.pause('recover')")
 p.locator('#import-json').set_input_files([
  dict(name='current.json',mimeType='application/json',buffer=raw),
  dict(name='legacy.json',mimeType='application/json',buffer=json.dumps(divergent).encode())])
 p.wait_for_function('window.paused');p.evaluate("document.querySelector('#page-refresh').click()")
 swipe(left);assert section()=='listening';assert p.evaluate('mobileProbe.busy()')
 p.evaluate('resume()');ready();assert data()==expected
 p.reload();ready();assert data()==expected
 print('PASS',engine,'raw-source export and verified branch recovery cannot be interrupted by refresh/swipe',flush=True)
 # A failed write retains the draft and rejects refresh.
 p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Keep failed draft');p.locator('#manual-artist').fill('Artist')
 p.evaluate("()=>{mobileProbe.failNextSave=true}")
 # Test-only save failure before publication.
 p.evaluate("()=>{mobileProbe.pause('save')}");p.locator('#save').click()
 p.wait_for_function('window.paused');p.evaluate('resume()');ready()
 expect(p.locator('#save-notice')).to_be_visible();n=len(dialogs)
 p.evaluate("document.querySelector('#page-refresh').click()")
 assert len(dialogs)==n+1;expect(p.locator('#manual-title')).to_have_value('Keep failed draft');assert data()==expected
 print('PASS',engine,'failed-save draft remains intact after refresh refusal',flush=True)
 # Pause initialization before migration; controls must remain inert until it settles.
 c.route(url,lambda r:r.fulfill(body=source.replace('const loaded=await lifecycle.init();','await new Promise(r=>window.releaseStartup=r);const loaded=await lifecycle.init();'),content_type='text/html'))
 other=c.new_page();other.goto(url,wait_until='domcontentloaded');other.wait_for_function('typeof window.releaseStartup==="function"')
 expect(other.locator('.shell')).to_have_attribute('inert','')
 other.evaluate("document.querySelector('#page-refresh').click()")
 expect(other.locator('.shell')).to_have_attribute('inert','')
 other.evaluate('releaseStartup()');other.wait_for_function('window.mobileProbe && !document.querySelector(".shell").inert')
 other.close()
 print('PASS',engine,'initialization/migration wait keeps the refresh UI inert',flush=True)
 assert not errors,errors
 print('PASS',engine,'three-section CRUD, JSON roundtrip, restore reload/swipe protection, zero page errors',flush=True)
 p.screenshot(path=f'/tmp/mla-mobile-{engine}.png',full_page=True)
 b.close();server.shutdown()

if __name__=='__main__':
 with sync_playwright() as pw:
  for engine in (sys.argv[1:] or ['chromium','webkit']):run(pw,engine)

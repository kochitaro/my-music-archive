"""Dense grid/list card gestures, no production source replacement.
Chromium: native CDP touch. WebKit: touch sequences + real tap/wheel at 390px.
WebKit wheel is unsupported in mobile mode, so its context uses a narrow desktop viewport.
Only synthetic records in isolated profiles; outbound requests blocked.
"""
import json, os, sys, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import QuietHandler
from data_preservation import seed_data
from mobile_navigation import TOUCH

CARD='#library button.coverbtn,#library button.listrow'


def run(pw, engine, url):
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if engine=='chromium' else pw.webkit.launch(executable_path=os.environ.get('MLA_WEBKIT'))
 c=b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=engine=='chromium')
 data=seed_data()
 for area in ['listening','collection','live']:
  data[area]=[{**data[area][0],'entryId':f'card-{area}-{i}','title':f'Synthetic {area} {i}'} for i in range(45)]
 c.add_init_script('localStorage.setItem("my-music-archive-pilot-v03",JSON.stringify('+json.dumps(data)+'))')
 c.route('https://**/*',lambda r:r.abort())
 p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 p.goto(url);p.evaluate('MLAReady')
 p.set_default_timeout(8000)
 session=c.new_cdp_session(p) if engine=='chromium' else None
 def area():return p.locator('#sections .active').get_attribute('data-section')
 def no_modal():expect(p.locator('.modal.open')).to_have_count(0)
 def swipe(selector,points):
  if session:
   for i,(x,y) in enumerate(points):
    session.send('Input.dispatchTouchEvent',{'type':'touchStart' if i==0 else 'touchMove','touchPoints':[dict(x=x,y=y)]})
    p.wait_for_timeout(35)
   session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
  else:p.evaluate(TOUCH,dict(selector=selector,points=points))
 def reset_scroll():
  p.evaluate('window.scrollTo({top:0,behavior:"instant"})')
  p.wait_for_function('scrollY===0')
 for layout in ['grid','list']:
  p.locator(f'#{layout}-tab').click()
  for current,next_area,direction in [('listening','collection',-1),('collection','live',-1),('live','collection',1)]:
   reset_scroll();p.locator(f'[data-section={current}]').click()
   cards=p.locator(CARD);expect(cards).to_have_count(45)
   card=cards.nth(1);card.scroll_into_view_if_needed()
   # Real tap still opens the correct record details.
   title=card.locator('.title').inner_text();card.tap()
   expect(p.locator('#view-modal')).to_have_class('modal open')
   assert title in p.locator('#view-content').inner_text()
   p.locator('#view-close').click();no_modal()
   reset_scroll();card.scroll_into_view_if_needed()
   target=card.locator('.art');box=target.bounding_box();y=box['y']+min(30,box['height']/2)
   # The list artwork is near the left edge; use its text for leftward gestures.
   if layout=='list':target=card.locator('.title');box=target.bounding_box();y=box['y']+box['height']/2
   start=200 if direction<0 else max(45,box['x']+min(20,box['width']/2))
   if layout=='list' and direction<0:start=min(300,box['x']+box['width']-5)
   points=[[start,y],[start+direction*30,y+1],[start+direction*70,y+2],[start+direction*130,y+2]]
   # Retain the detached original to test delayed clicks after render replaces cards.
   card.evaluate('(el)=>{window.originalSwipeCard=el}')
   selector='#library button:nth-of-type(2) '+('.title' if layout=='list' else '.art')
   swipe(selector,points)
   assert area()==next_area,(engine,layout,current,area())
   no_modal()
   p.evaluate("""()=>{
    const card=document.querySelector('#library button.coverbtn,#library button.listrow');
    const end=new Event('touchend',{bubbles:true});Object.defineProperties(end,{touches:{value:[]},changedTouches:{value:[{identifier:42}]}});card.dispatchEvent(end);
    for(const el of [originalSwipeCard,card])el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,detail:1}));
   }""")
   assert area()==next_area;no_modal()
   # A new deliberate touch must work immediately, despite the prior swipe guard.
   card=p.locator(CARD).nth(1);card.scroll_into_view_if_needed();card.tap()
   expect(p.locator('#view-modal')).to_have_class('modal open');p.locator('#view-close').click()
   # Vertical motion on a card keeps native scrolling available and never opens details.
   reset_scroll();card=p.locator(CARD).nth(1);card.scroll_into_view_if_needed()
   box=card.bounding_box();x=box['x']+min(box['width']/2,90);y=box['y']+30
   before=p.evaluate('scrollY')
   if session:
    swipe('',[[x,y],[x,y-40],[x,y-100],[x,y-160]])
    p.wait_for_function('(before)=>scrollY>before',arg=before)
    p.wait_for_timeout(1800) # settle native momentum before the next case
   else:
    result=p.evaluate(TOUCH,dict(selector='#library button:nth-of-type(2)',points=[[200,500],[198,470],[197,400],[196,330]]))
    assert not any(result)
    p.mouse.move(x,y);p.mouse.wheel(0,350);p.wait_for_function('(before)=>scrollY>before',arg=before)
   assert area()==next_area;no_modal()
   print('PASS',engine,layout,current,'45 dense cards: tap details, horizontal switch once, ghost-click suppression, immediate new tap, vertical scroll',flush=True)
   reset_scroll();p.wait_for_timeout(750)
  # Edge starts, diagonal/cancel/multitouch remain rejected even on allowed cards.
  p.locator('[data-section=listening]').click()
  selector='#library button:nth-of-type(2) .title'
  for points,extra in [([[5,400],[160,400]],{}),([[385,400],[200,400]],{}),([[200,500],[170,460],[80,350]],{}),([[220,400],[150,400],[70,400]],{'cancel':True}),([[220,400],[150,400],[70,400]],{'multi':True})]:
   p.evaluate(TOUCH,dict(selector=selector,points=points,**extra));assert area()=='listening';no_modal()
  p.wait_for_timeout(750)
 # A real nested control is still excluded, as are horizontal scroll descendants.
 p.evaluate("""()=>{const card=document.querySelector('#library button.coverbtn,#library button.listrow');
 const input=document.createElement('input');input.id='nested-input';card.append(input);
 const slider=document.createElement('span');slider.id='nested-slider';slider.setAttribute('role','slider');card.append(slider);
 const scroll=document.createElement('div');scroll.style='width:50px;overflow-x:auto';scroll.innerHTML='<span id="nested-wide" style="display:block;width:200px">wide</span>';card.append(scroll)}""")
 for selector in ['#nested-input','#nested-slider','#nested-wide','#grid-tab','#query']:
  result=p.evaluate(TOUCH,dict(selector=selector,points=[[240,400],[170,400],[80,400]]));assert not any(result);assert area()=='listening'
 p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Unsaved input');p.locator('#manual-artist').fill('Synthetic')
 slider=p.locator('#modal .star-rating').first;slider.scroll_into_view_if_needed();box=slider.bounding_box()
 before=p.locator('#rating').input_value();p.touchscreen.tap(box['x']+box['width']*.7,box['y']+box['height']/2)
 assert p.locator('#rating').input_value()!=before;assert area()=='listening'
 p.evaluate(TOUCH,dict(selector='#modal .star-rating',points=[[240,400],[170,400],[80,400]]));assert area()=='listening'
 expect(p.locator('#manual-title')).to_have_value('Unsaved input');p.locator('#close').click()
 print('PASS',engine,'edge/diagonal/cancel/multitouch and nested controls excluded; rating/input/modal preserved; page errors 0',flush=True)
 assert not errors,errors
 b.close()

if __name__=='__main__':
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 with sync_playwright() as pw:
  for engine in (sys.argv[1:] or ['chromium','webkit']):run(pw,engine,f'http://127.0.0.1:{server.server_port}/')
 server.shutdown()

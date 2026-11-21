"""Native Chromium touch dispatch and native wheel scrolling in both engines.
No application source injection. Run: python -u tests/mobile_navigation_native.py
"""
import json, os, sys, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import QuietHandler
from data_preservation import seed_data


def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 data=seed_data()
 data['listening']=[{**data['listening'][0],'entryId':f'native-{i}','title':f'Native {i}'} for i in range(50)]
 with sync_playwright() as pw:
  for engine in (sys.argv[1:] or ['chromium','webkit']):
   b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if engine=='chromium' else pw.webkit.launch(executable_path=os.environ.get('MLA_WEBKIT'))
   c=b.new_context(viewport={'width':390,'height':844},is_mobile=engine=='chromium',has_touch=True)
   c.add_init_script('localStorage.setItem("my-music-archive-pilot-v03",JSON.stringify('+json.dumps(data)+'))')
   c.route('https://**/*',lambda r:r.abort());p=c.new_page()
   p.goto(f'http://127.0.0.1:{server.server_port}/');p.evaluate('MLAReady')
   if engine=='chromium':
    session=c.new_cdp_session(p)
    def drag(xs,ys):
     for i,(x,y) in enumerate(zip(xs,ys)):
      session.send('Input.dispatchTouchEvent',{'type':'touchStart' if i==0 else 'touchMove','touchPoints':[dict(x=x,y=y)]})
     session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    box=p.locator('#library-title').bounding_box();y=box['y']+box['height']/2
    drag([200,160,100,40],[y]*4)
    expect(p.locator('[data-section=collection]')).to_have_class('tab active')
    p.wait_for_timeout(750)
    box=p.locator('#library-title').bounding_box();y=box['y']+box['height']/2
    drag([100,150,220,320],[y]*4)
    expect(p.locator('[data-section=listening]')).to_have_class('tab active')
    p.wait_for_timeout(750)
    box=p.locator('#library-title').bounding_box();y=box['y']+box['height']/2
    drag([200]*5,[y,y-40,y-100,y-180,60])
    p.wait_for_function('scrollY>0')
    expect(p.locator('[data-section=listening]')).to_have_class('tab active')
    expect(p.locator('.modal.open')).to_have_count(0)
    print('PASS chromium native touch left/right switch once, vertical touch scroll, no accidental modal',flush=True)
    p.wait_for_timeout(750)
   p.mouse.move(380,500);p.mouse.wheel(0,650)
   p.wait_for_function('scrollY>=400')
   expect(p.locator('#back-to-top')).to_be_visible()
   p.wait_for_timeout(2000)  # Let native fling/wheel momentum settle before testing smooth scroll.
   p.locator('#back-to-top').click();p.wait_for_function('scrollY===0')
   expect(p.locator('#back-to-top')).to_be_hidden()
   p.screenshot(path=f'/tmp/mla-mobile-layout-{engine}.png',full_page=False)
   assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
   print('PASS',engine,'native wheel scroll + smooth top on 390px viewport; no horizontal page overflow',flush=True)
   b.close()
 server.shutdown()

if __name__=='__main__':main()

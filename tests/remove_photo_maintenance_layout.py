"""Full-page before/after images and unchanged app areas, JA/EN x five widths."""
import json, subprocess, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from ui_v0322 import ROOT, KEY, QuietHandler
from group_display_live import seed, PREF

OUT=ROOT/'docs/remove-photo-maintenance-evidence/layout'
BASE='6bbe6e43ae9886674e2a51d0cc0b8b43ca330164'


def main():
 OUT.mkdir(parents=True,exist_ok=True)
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
 url=f'http://127.0.0.1:{server.server_port}/';old=subprocess.check_output(['git','show',BASE+':index.html'],cwd=ROOT).decode();results=[];errors=[]
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for lang in ['ja','en']:
   for width in [320,375,390,430,1280]:
    phases={}
    for phase in ['before','after']:
     c=b.new_context(viewport=dict(width=width,height=844),has_touch=True);c.route('https://**/*',lambda r:r.abort())
     if phase=='before':c.route(url,lambda r:r.fulfill(body=old,content_type='text/html'))
     p=c.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.goto(url);p.evaluate('async()=>await MLAReady')
     prefs=dict(listening=['genre','rating'],collection=['label'],live=['artists','venue','rating'])
     p.evaluate('([k,s,l,pk,v])=>{localStorage.setItem(k,JSON.stringify(s));localStorage.setItem("mma-ui-language",l);localStorage.setItem(pk,JSON.stringify(v))}',[KEY,seed,lang,PREF,prefs]);p.reload();p.evaluate('async()=>await MLAReady');p.wait_for_function("localStorage.getItem('my-music-archive-photos-v1')!==null")
     raw=p.evaluate("localStorage.getItem('my-music-archive-photos-v1')");legacy=p.evaluate('(k)=>localStorage.getItem(k)',KEY)
     if phase=='after':
      assert p.locator('#photo-maintenance,[id^=photo-export],#photo-verify,#photo-cleanup,#photo-recovery-file,#photo-recover').count()==0
      assert p.locator('#backup-guide').evaluate('(e)=>e.parentElement.nextElementSibling.matches("footer.foot")')
      assert p.locator('#storage-state').is_hidden()
     phases[phase]={}
     for area in ['listening','collection','live']:
      p.locator(f'[data-section={area}]').click()
      for screen in ['archive','insights']:
       p.locator('#'+screen+'-screen').click()
       p.locator('#library img').evaluate_all('(ns)=>Promise.all(ns.map(n=>n.decode().catch(()=>{})))')
       name=f'{phase}-{area}-{screen}-{lang}-{width}.png'
       p.screenshot(path=str(OUT/name),full_page=True,animations='disabled')
       assert p.locator('footer.foot').is_visible()
       assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
       ids=['sections','screen-switch','search-panel','archive-panel','insights-content']
       p.evaluate('scrollTo(0,0)')
       fields={i:p.locator('#'+i).evaluate('(e)=>({html:e.innerHTML,rect:(()=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height]})()})') for i in ids}
       fields['footer']=p.locator('footer.foot').inner_html()
       if screen=='archive':
        p.locator('#list-tab').click();fields['list']=p.locator('#library').inner_html();p.locator('#grid-tab').click()
       phases[phase][area,screen]=fields
     assert p.evaluate("localStorage.getItem('my-music-archive-photos-v1')")==raw
     assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==legacy
     c.close()
    for key,value in phases['before'].items():
     assert value==phases['after'][key],(lang,width,key)
     results.append(dict(lang=lang,width=width,area=key[0],screen=key[1],appDOMAndGeometryEqual=True,footerUnchanged=True,legacyRetained=True))
    print('PASS layout',lang,width,'all 3 archives / Insights / list exact; removed panel; footer adjacent; no overflow; records unchanged',flush=True)
  b.close()
 assert not errors,errors
 (OUT/'comparison.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
 server.shutdown();print('PASS 60 comparisons; 120 full-page PNGs; page errors 0',flush=True)


if __name__=='__main__':main()

"""Compare latest main to IndexedDB integration using synthetic data, no external requests."""
import json, subprocess, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from ui_v0322 import ROOT, KEY, QuietHandler
from group_display_live import seed, PREF
OUT=ROOT/"docs/indexeddb-integration-evidence"
OUT.mkdir(exist_ok=True)
BASE="c2c719dd1bd25583402e0a2db948e168018ce34e"

def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/';old=subprocess.check_output(['git','show',BASE+':index.html']).decode();results=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for lang in ['ja','en']:
   for width in [320,375,390,430,1280]:
    phases={}
    for phase in ['before','after']:
     c=browser.new_context(viewport=dict(width=width,height=844),has_touch=True,accept_downloads=True);c.route('https://**/*',lambda r:r.abort())
     if phase=='before':c.route(url,lambda r:r.fulfill(body=old,content_type='text/html'))
     p=c.new_page();p.goto(url);prefs=dict(listening=['genre','rating'],collection=['label'])
     p.evaluate('([k,s,l,pk,v])=>{localStorage.setItem(k,JSON.stringify(s));localStorage.setItem("mma-ui-language",l);localStorage.setItem(pk,JSON.stringify(v))}',[KEY,seed,lang,PREF,prefs]);p.reload();p.wait_for_function("document.querySelector('#display-options') && (!window.MLAReady || document.querySelector('#photo-maintenance'))");phases[phase]={}
     for area in ['listening','collection','live']:
      p.locator(f'[data-section={area}]').click();p.locator('#sort-toggle').click();p.locator('#sort').select_option('date-desc' if area=='live' else 'release-desc');p.locator('#group').select_option('year');p.locator('#sort-toggle').click()
      # DOM/geometry equality provides compact repeatable evidence.
      photos=p.locator('.coverbtn .art').evaluate_all('(ns)=>ns.map(n=>({w:n.getBoundingClientRect().width,h:n.getBoundingClientRect().height,src:n.getAttribute("src"),class:n.className}))')
      cards=p.locator('.album-tile').evaluate_all('''ns=>ns.map(n=>{const r=n.getBoundingClientRect();return {w:r.width,h:r.height,text:n.textContent,children:[...n.querySelectorAll('.art,.title,.muted.small,.tile-slot')].map(e=>{const x=e.getBoundingClientRect();return [x.x-r.x,x.y-r.y,x.width,x.height]})}})''')
      heading=p.locator('#library > h3').first.bounding_box();card=p.locator('.coverbtn').first.bounding_box();panel_y=p.locator('#archive-panel').bounding_box()['y']
      p.locator('#list-tab').click();listing=p.locator('#library .listrow').evaluate_all('(ns)=>ns.map(n=>n.outerHTML)');p.locator('#grid-tab').click()
      p.locator('#insights-screen').click();insights=p.locator('#'+area+'-insights').inner_html();p.locator('#archive-screen').click()
      phases[phase][area]=dict(photos=photos,cards=cards,list=listing,insights=insights,heading=heading,card=card,cardOffset=card['y']-panel_y)
     if phase=='after':
      archive=p.evaluate("localStorage.getItem('my-music-archive-photos-v1')")
      p.locator('[data-section=live]').click();p.locator('#display-options').click();p.locator('[data-display-field=artists]').check();p.locator('[data-display-field=rating]').check();p.locator('#display-close').click()
      pref=p.evaluate('(k)=>localStorage.getItem(k)',PREF);p.locator('#ui-language').select_option('en' if lang=='ja' else 'ja');p.locator('#ui-language').select_option(lang);assert p.evaluate('(k)=>localStorage.getItem(k)',PREF)==pref
      assert p.locator('.live-tile .tile-slot').first.get_attribute('data-field')=='artists'
      p.locator('#display-options').click();p.locator('[data-move=up][data-field=rating]').click();p.locator('#display-close').click()
      p.reload();p.locator('[data-section=live]').click()
      assert p.locator('.live-tile .tile-slot').first.get_attribute('data-field')=='rating'
      assert p.evaluate("localStorage.getItem('my-music-archive-photos-v1')")==archive
      prefs_saved=p.evaluate('(k)=>JSON.parse(localStorage.getItem(k))',PREF)
      assert prefs_saved==dict(prefs,live=['rating','artists'])
      with p.expect_download() as d:p.locator('#export-json').click()
      with open(d.value.path()) as f:assert json.load(f)==seed
     c.close()
    for area in ['listening','collection','live']:
     a=phases['before'][area];b=phases['after'][area]
     for field in ['photos','cards','list','insights']:assert a[field]==b[field],(lang,width,area,field)
     delta=b['cardOffset']-a['cardOffset'];assert abs(delta)<=1,(lang,width,area,delta)
     results.append(dict(lang=lang,width=width,area=area,photosUnchanged=True,albumCardsUnchanged=(area!='live'),listUnchanged=True,insightsUnchanged=True,headingBefore=a['heading'],headingAfter=b['heading'],cardStartDelta=delta))
    print('PASS compare',lang,width,'album cards/list/Insights/photos unchanged; grouped card start delta <=1px; JSON exact; Live language retained',flush=True)
  browser.close()
 (OUT/'main-comparison.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

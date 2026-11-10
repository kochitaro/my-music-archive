"""Compare default card geometry/content to the exact main used as the implementation base."""
import json, subprocess, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from display_options import seed, EVIDENCE
from ui_v0322 import KEY, QuietHandler
BASE='b6f6e435255f1af52a55fa3d75b4e2cd0c499d96'
server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
baseline=subprocess.check_output(['git','show',BASE+':index.html']).decode();url=f'http://127.0.0.1:{server.server_port}/';results=[]
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 for lang in ['ja','en']:
  for width in [320,375,390,430,1280]:
   c=b.new_context(viewport=dict(width=width,height=844));c.route('https://**/*',lambda r:r.abort());p=c.new_page();p.goto(url);p.evaluate('([k,s,l])=>{localStorage.setItem(k,JSON.stringify(s));localStorage.setItem("mma-ui-language",l)}',[KEY,seed,lang])
   phases={}
   for phase in ['before','after']:
    if phase=='before':c.route(url,lambda r:r.fulfill(body=baseline,content_type='text/html'))
    else:c.unroute(url)
    p.reload();phases[phase]={}
    for area in ['listening','collection']:
     p.locator(f'[data-section={area}]').click();p.locator('#sort-toggle').click();p.locator('#group').select_option('none')
     for sort in ['release-desc','date-desc','rating-desc']:
      p.locator('#sort').select_option(sort)
      phases[phase][area+sort]=p.locator('.album-tile').evaluate_all('''ns=>ns.map(n=>{const card=n.getBoundingClientRect();return [...n.querySelectorAll('.art,.title,.muted.small,.tile-rating,.tile-date')].map(e=>{const r=e.getBoundingClientRect();return {class:e.className,text:e.textContent,x:r.x-card.x,y:r.y-card.y,w:r.width,h:r.height}})})''')
   assert phases['before']==phases['after'],(lang,width)
   results.append(dict(lang=lang,width=width,defaultCardGeometryAndContentUnchanged=True))
   c.close()
 b.close()
(EVIDENCE/'default-comparison.json').write_text(json.dumps(results,indent=2));print('PASS exact default card geometry/content: 2 languages × 5 widths × 2 archives × 3 sorts')

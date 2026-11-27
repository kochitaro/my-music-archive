"""Visual/DOM boundaries using only synthetic inputs and production render()."""
import threading
from datetime import datetime,timezone
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from ui_v0322 import QuietHandler
from insights_polish import E

def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);p=browser.new_page(viewport=dict(width=320,height=844));p.route('https://**/*',lambda r:r.abort());p.clock.set_fixed_time(datetime(2026,11,27,tzinfo=timezone.utc));p.goto(f'http://127.0.0.1:{server.server_port}');p.evaluate('MLAReady');p.locator('#insights-screen').click()
  for n in [0,1,15,16,80]:
   p.evaluate('n=>MLAInsights.render(document.querySelector("#listening-insights"),Array.from({length:n},(_,i)=>({genre:"長い分類名 Long category "+i})),"listening",false,new Date(2026,10,27))',n)
   cat=p.locator('[data-insight=genre]');assert cat.locator('circle').count()==min(n,16)
   if n:
    assert cat.locator('.insight-center strong').inner_text()==str(n)
    assert cat.evaluate('(e)=>[...e.querySelectorAll("circle")].every((c,i)=>getComputedStyle(c).stroke===getComputedStyle(e.querySelectorAll(".insight-swatch")[i]).backgroundColor)')
  p.evaluate('''()=>MLAInsights.render(document.querySelector('#listening-insights'),Array.from({length:12000},(_,i)=>({genre:i?'Large':'Tiny'})),'listening',false,new Date(2026,10,27))''');assert p.locator('[data-insight=genre] circle').evaluate_all('(nodes)=>nodes.every(e=>parseFloat(e.getAttribute("stroke-dasharray"))>0)');p.locator('[data-insight=genre]').screenshot(path=str(E/'tiny-segment-320.png'))
  for months in [1,2,12,27]:
   p.evaluate('n=>{const k=2026*12+10-n+1;MLAInsights.render(document.querySelector("#listening-insights"),[{date:Math.floor(k/12)+"-"+String(k%12+1).padStart(2,"0")}],"listening",false,new Date(2026,10,27))}',months)
   time=p.locator('[data-insight=time]');assert time.locator('li').count()==min(12,months)
   assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
  print('PASS 0/1/15/16/80 categories, exact totals, matching colors, tiny segment survives, 1/2/12/27-month timelines at 320px',flush=True);browser.close()
 server.shutdown()
if __name__=='__main__':main()

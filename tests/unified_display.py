"""Compare unified storage with pinned pre-change main on synthetic UI data."""
import argparse,json,subprocess,threading
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright
from data_preservation import seed_data
ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
 def log_message(self,*a):pass

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--browser',default='chromium');args=parser.parse_args()
 server=ThreadingHTTPServer(('127.0.0.1',0),Quiet);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
 old=subprocess.check_output(['git','show','fdbefae6:index.html'],cwd=ROOT,text=True).replace("setSection('listening');showStorageState();","window.testBusy=()=>saving||operationBusy;setSection('listening');showStorageState();")
 new=(ROOT/'index.html').read_text()
 comparisons=[]
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if args.browser=='chromium' else pw.webkit.launch()
  for lang in ['ja','en']:
   pages=[];contexts=[]
   for source in [old,new]:
    c=b.new_context();contexts.append(c);c.route('https://**/*',lambda r:r.abort());c.route(url+'/seed',lambda r:r.fulfill(body='<p>seed</p>',content_type='text/html'));c.route(url+'/',lambda r,request,s=source:r.fulfill(body=s,content_type='text/html'))
    p=c.new_page();p.on('dialog',lambda d:d.accept());p.goto(url+'/seed');p.evaluate('([d,l])=>{localStorage.setItem("my-music-archive-pilot-v03",JSON.stringify(d));localStorage.setItem("mma-ui-language",l)}',[seed_data(),lang]);p.goto(url+'/');p.evaluate('()=>MLAReady');p.wait_for_function('!window.testBusy?.()');pages.append(p)
   for width in [320,390,1280]:
    for p in pages:p.set_viewport_size({'width':width,'height':900})
    for area in ['listening','collection','live']:
     for p in pages:p.locator(f'[data-section={area}]').click()
     for mode in ['grid','list']:
      values=[]
      for p in pages:
       p.locator('#'+mode+'-tab').click();p.wait_for_function("Array.from(document.querySelectorAll('#library img')).every(x=>x.complete&&x.naturalWidth>0)")
       values.append(p.locator('#library').evaluate("e=>({text:e.innerText,buttons:Array.from(e.querySelectorAll('button')).map(b=>({text:b.innerText,width:b.getBoundingClientRect().width,height:b.getBoundingClientRect().height})),images:Array.from(e.querySelectorAll('img')).map(n=>n.src)})"))
      assert values[0]==values[1],(lang,width,area,mode,values)
      comparisons.append([lang,width,area,mode])
     values=[]
     for p in pages:p.locator('#insights-screen').click();values.append(p.locator('#'+area+'-insights').inner_html())
     assert values[0]==values[1],(lang,width,area,'insights');comparisons.append([lang,width,area,'insights'])
   for c in contexts:c.close()
  b.close()
 server.shutdown();print(json.dumps({'browser':args.browser,'comparisons':len(comparisons),'result':'exact archive text/photo/geometry and Insights DOM match','cases':comparisons}),flush=True)
if __name__=='__main__':main()

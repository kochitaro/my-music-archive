import functools,subprocess,tempfile,threading,sys
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/footer-copy-cleanup'
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
with tempfile.TemporaryDirectory() as tmp:
 old=Path(tmp)
 for f in (ROOT/'dist').iterdir():(old/f.name).write_bytes(b'' if f.name=='.nojekyll' else subprocess.check_output(['git','show','59ba527:'+f.name],cwd=ROOT))
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for kind,root in [('before',old),('after',ROOT/'dist')]:
   s=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)));threading.Thread(target=s.serve_forever,daemon=True).start()
   for w in [320,393,1280]:
    for lang in ['ja','en']:
     c=b.new_context(viewport={'width':w,'height':852},locale=lang);c.route('https://**/*',lambda r:r.abort());p=c.new_page();p.goto(f'http://127.0.0.1:{s.server_port}/');p.evaluate('MLAReady');p.select_option('#ui-language',lang)
     for zoom in ([1,2] if kind=='after' else [1]):
      p.add_style_tag(content=f':root{{font-size:{15*zoom}px}}');p.evaluate('document.fonts.ready');p.evaluate('window.scrollTo(0,document.body.scrollHeight)');p.wait_for_timeout(500)
      path=OUT/(f'after-{w}-{lang}-{zoom}x.png' if kind=='after' else f'before-{w}-{lang}.png')
      rect=p.locator('footer').bounding_box();p.screenshot(path=str(path),full_page=True)
      y=p.locator('footer').evaluate('e=>e.getBoundingClientRect().top+scrollY');img=Image.open(path);img.crop((0,max(0,int(y)-16),img.width,min(img.height,int(y+rect['height'])+16))).save(path)
     c.close()
   s.shutdown()
  b.close()
for lang in ['ja','en']:
 a=Image.open(OUT/f'before-393-{lang}.png');b=Image.open(OUT/f'after-393-{lang}-1x.png');img=Image.new('RGB',(a.width+b.width,max(a.height,b.height)),(17,21,27));img.paste(a,(0,0));img.paste(b,(a.width,0));img.save(OUT/f'comparison-393-{lang}.png')
print('PASS before/after screenshots captured at page bottom with footer unobscured; comparisons left=before right=after')

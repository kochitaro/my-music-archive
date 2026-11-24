"""Compare current UI with the main baseline; measure native-select ink, not iOS claims."""
import io,json,os,subprocess,threading
from http.server import ThreadingHTTPServer
from PIL import Image
from playwright.sync_api import sync_playwright,expect
from ui_v0322 import ROOT,KEY,QuietHandler,album
OUT=ROOT/'docs/archive-top-spacing-language';OUT.mkdir(exist_ok=True)
BASE='3a50e8392e33631961d234cb6bd494e78dfca53f'
old=subprocess.check_output(['git','show',BASE+':index.html'],text=True)
seed=dict(version=3,listening=[album('Listening '+str(i)) for i in range(12)],collection=[album('Collection')],live=[dict(entryId='live',title='Live',date='2026-01-02')])
server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/'
def geometry(p):
 return p.evaluate('''()=>{const r=s=>{const b=document.querySelector(s).getBoundingClientRect();return {x:b.x,y:b.y,w:b.width,h:b.height}};return {panel:r('#archive-panel'),library:r('#library'),year:r('#library h3'),card:r('#library .coverbtn'),art:r('#library .art'),select:r('#ui-language'),bar:r('.langbar'),label:r('.langbar label'),panelInset:parseFloat(getComputedStyle(document.querySelector('#archive-panel')).paddingTop)+parseFloat(getComputedStyle(document.querySelector('#archive-panel')).borderTopWidth),headingMargin:getComputedStyle(document.querySelector('#library h3')).marginTop,libraryMargin:getComputedStyle(document.querySelector('#library')).marginTop}}''')
def saved_language(p,lang):
 p.wait_for_function("""async lang=>new Promise(resolve=>{const r=indexedDB.open('mla-archive-v1');r.onsuccess=()=>{const db=r.result;const q=db.transaction('settings').objectStore('settings').get('current');q.onsuccess=()=>{db.close();resolve(q.result?.language===lang)}}})""",arg=lang)
def ink(p):
 # 3x screenshot; ignore borders and the separate arrow area at x>=width-22px.
 im=Image.open(io.BytesIO(p.locator('#ui-language').screenshot())).convert('RGB');w,h=im.size
 pts=[x for y in range(18,h-18) for x in range(12,w-66) if min(im.getpixel((x,y)))>150]
 left,right=min(pts)/3,(max(pts)+1)/3
 return dict(left=left,right=right,center=(left+right)/2,boxCenter=w/6,offset=(left+right)/2-w/6)
results=[]
with sync_playwright() as pw:
 for engine in ['chromium','webkit']:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']) if engine=='chromium' else pw.webkit.launch(executable_path=os.environ.get('MLA_WEBKIT'))
  for width in [390,1280]:
   before={}
   for phase in ['before','after']:
    c=b.new_context(viewport=dict(width=width,height=844),has_touch=width==390,is_mobile=width==390,device_scale_factor=3)
    c.route('https://**/*',lambda r:r.abort());c.add_init_script('if(!localStorage.getItem('+json.dumps(KEY)+'))localStorage.setItem('+json.dumps(KEY)+','+json.dumps(json.dumps(seed))+')')
    p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    if phase=='before':p.route(url,lambda r:r.fulfill(body=old,content_type='text/html'))
    p.goto(url);p.wait_for_function('!document.querySelector("main").inert')
    for lang in ['ja','en']:
     p.select_option('#ui-language',lang);expect(p.locator('html')).to_have_attribute('lang',lang)
     for area in ['listening','collection','live']:
      p.locator(f'[data-section={area}]').click();p.evaluate('scrollTo(0,0)');p.wait_for_timeout(60)
      g=geometry(p)
      if phase=='before':before[lang,area]=g
      else:
       prior=before[lang,area]
       assert abs(prior['year']['y']-g['year']['y']-16)<.1
       assert abs(g['year']['y']-g['panel']['y']-g['panelInset'])<.1, (g,prior)
       assert g['libraryMargin']=='0px' and g['headingMargin']=='0px'
       for part in ['card','art']:
        assert all(g[part][dim]==prior[part][dim] for dim in ['w','h']), (part,g,prior)
       assert abs((g['card']['y']-g['year']['y'])-(prior['card']['y']-prior['year']['y']))<.1
       assert p.locator('#archive-panel').get_attribute('aria-labelledby')=='library-title'
       assert 'heading' in p.locator('#archive-panel').aria_snapshot()
       p.locator('#display-options').click();expect(p.locator('#display-modal')).to_have_class('modal open');p.locator('#display-close').click()
      if width==390:
       p.evaluate('scrollTo(0,0)');p.wait_for_timeout(80)
       p.screenshot(path=str(OUT/f'{engine}-{lang}-{area}-{phase}.png'),scale='css')
      results.append(dict(engine=engine,width=width,lang=lang,area=area,phase=phase,panelToYear=g['year']['y']-g['panel']['y']))
     p.wait_for_timeout(300);p.evaluate('scrollTo(0,document.body.scrollHeight)');p.wait_for_timeout(80)
     g=geometry(p);glyph=ink(p)
     if phase=='before':before[lang,'language']=(g,glyph)
     else:
      prior=before[lang,'language'][0]
      for part in ['select','bar','label']:
       assert all(g[part][dim]==prior[part][dim] for dim in ['x','w','h']),(part,g,prior)
      assert abs(glyph['offset'])<=1.5,glyph
      assert p.locator('#ui-language').evaluate('e=>getComputedStyle(e).paddingLeft')=='0px'
      assert p.locator('#sort').evaluate('e=>getComputedStyle(e).textAlignLast')!='center'
     if width==390:p.screenshot(path=str(OUT/f'{engine}-{lang}-language-{phase}.png'),scale='css')
     results.append(dict(engine=engine,width=width,lang=lang,phase=phase,ink=glyph,select=g['select']))
    if phase=='after':
     saved_language(p,'en');p.reload();p.wait_for_function('!document.querySelector("main").inert');assert p.locator('#ui-language').input_value()=='en'
     p.select_option('#ui-language','ja');saved_language(p,'ja');p.reload();p.wait_for_function('!document.querySelector("main").inert');assert p.locator('#ui-language').input_value()=='ja'
    assert not errors,errors
    c.close()
   print('PASS',engine,width,'ja/en 3 areas: top margin -16px; year-card gap and card/art sizes unchanged; settings/labels; language box+right alignment unchanged; ink center <=1.5px; persistence',flush=True)
  b.close()
(OUT/'measurements.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
server.shutdown()

"""Round-two Insights: isolated synthetic Chromium; never iPhone Safari."""
import json,threading,subprocess
from datetime import datetime,timezone
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from data_preservation import PHOTO
from ui_v0322 import ROOT,KEY,QuietHandler
E=ROOT/'docs/insights-polish-02';E.mkdir(exist_ok=True)
SNAP='''async()=>{const db=await new Promise((res,rej)=>{const q=indexedDB.open('mla-archive-v1');q.onsuccess=()=>res(q.result);q.onerror=()=>rej(q.error)});const out={};for(const store of ['archive','photos','settings','meta'])out[store]=await new Promise((res,rej)=>{const tx=db.transaction(store),s=tx.objectStore(store),k=s.getAllKeys(),v=s.getAll();tx.oncomplete=()=>res([k.result,v.result]);tx.onerror=()=>rej(tx.error)});db.close();return JSON.stringify(out)}'''
SEED=dict(version=3,listening=[dict(entryId='album'+str(i),id='',title='Album '+str(i),artist='Artist '+str(i),genre='Genre '+str(i),label='Label '+str(i),tags=['Tag '+str(i)],rating=str(10-i%11),date='2024-09-01' if i<20 else '2026-11-01',release='2020' if i==39 else '2000',photo=PHOTO if i==0 else '') for i in range(40)],collection=[],live=[])
SEED['listening'][0].update(title='長い作品名 Long album title '*8,artist='長いアーティスト Long artist '*8)
SEED['listening'][1]['id']='12345678-1234-1234-1234-123456789abc'
SEED['listening'][2]['rating']='';SEED['listening'][3].update(date='',release='')
SEED['collection']=SEED['listening'][:]
SEED['live']=[dict(entryId='show'+str(i),title='Show',artists=['Artist'],venue='Venue '+str(i),date=str(1972+i)+'-05-01') for i in range(55) if i%3!=1]
def order(root):return root.locator(':scope > [data-insight]').evaluate_all('(nodes)=>nodes.map(e=>e.dataset.insight)')
def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  def context(width=390,lang='en',seed=SEED):
   ctx=browser.new_context(viewport=dict(width=width,height=844),is_mobile=True,has_touch=True);ctx.route('https://**/*',lambda r:r.abort())
   ctx.add_init_script('if(!localStorage.getItem('+json.dumps(KEY)+'))localStorage.setItem('+json.dumps(KEY)+','+json.dumps(json.dumps(seed))+');localStorage.setItem("mma-ui-language",'+json.dumps(lang)+')')
   p=ctx.new_page();p.set_default_timeout(8000);p.clock.set_fixed_time(datetime(2026,11,27,tzinfo=timezone.utc));p.goto(base);p.evaluate('MLAReady');return ctx,p
  def area(p,name):
   p.locator(f'[data-section={name}]').click();p.locator('#insights-screen').click();return p.locator('#'+name+'-insights')
  for width in [320,375,390,393,430]:
   for lang in ['ja','en']:
    ctx,p=context(width,lang);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    more='さらに表示' if lang=='ja' else 'Show more';yearly='年別' if lang=='ja' else 'Yearly'
    for name in ['listening','collection','live']:
     root=area(p,name);assert root.locator('.insight-settings').get_attribute('aria-label')==('表示設定' if lang=='ja' else 'Display Settings')
     if name=='collection':expect(root.locator('.insight-heading h2')).to_have_text('購入の統計' if lang=='ja' else 'Collection Insights')
     icon=root.locator('.insight-settings').bounding_box();h=root.locator('.insight-heading').bounding_box();assert icon['width']>=44 and abs(icon['x']+icon['width']-h['x']-h['width'])<1
     if name=='listening':assert order(root)==['artists','score','genre','tags','label','time','release']
     cat=root.locator('[data-insight='+('venue' if name=='live' else 'genre')+']');assert cat.locator('circle').count()==16
     assert cat.locator('circle').first.get_attribute('stroke-width')=='35';assert cat.locator('.insight-record-grooves').count()==1
     assert cat.locator('.insight-center strong').inner_text()==str(len(SEED[name]))
     assert cat.locator('circle').evaluate_all('(nodes)=>nodes.every(e=>Number(e.getAttribute("stroke-dasharray").split(" ")[0])>0)')
     time=root.locator('[data-insight=time]')
     if name!='live':
      assert time.locator('li').count()==12;assert time.locator('.insight-name').first.inner_text()=='2026-11'
      scale=time.locator('.insight-fill').first.get_attribute('style');time.get_by_role('button',name=more,exact=True).click();assert time.locator('li').count()==24;assert time.locator('.insight-fill').first.get_attribute('style')==scale
      time.get_by_role('button',name=more,exact=True).click();assert time.locator('li').count()==27;assert time.get_by_role('button',name=more,exact=True).count()==0
      assert time.locator('.insight-name').last.inner_text()=='2024-09';assert '0' in time.locator('.insight-count').all_inner_texts()
      if width==390:time.screenshot(path=str(E/f'{name}-{lang}-monthly.png'))
      time.get_by_role('button',name=yearly,exact=True).click();assert time.locator('li').count()==3
      rel=root.locator('[data-insight=release]');rel.get_by_role('button',name='年代別' if lang=='ja' else 'By Decade',exact=True).click();assert rel.locator('svg').count()==0
      assert rel.locator('.insight-name').first.inner_text()==('2020年代' if lang=='ja' else '2020s')
      if width==390:rel.screenshot(path=str(E/f'{name}-{lang}-decades.png'))
     else:
      assert time.locator('select').input_value()=='2026';assert time.locator('.insight-column').count()==12
      time.locator('select').select_option('1972');assert time.locator('.insight-column-count').all_text_contents()[:4]==['—']*4,time.locator('.insight-column-count').all_text_contents()
      time.locator('select').select_option('1973');assert time.locator('.insight-column-count').all_text_contents()==['0']*12
      time.evaluate('(e)=>scrollTo(0,e.getBoundingClientRect().top+scrollY-80)');before=time.locator('h3').bounding_box()['y'];time.locator('select').select_option('2026');assert abs(time.locator('h3').bounding_box()['y']-before)<3
      if width==390:time.screenshot(path=str(E/f'live-{lang}-monthly.png'))
      time.get_by_role('button',name=yearly,exact=True).click();assert time.locator('svg').count()==1;assert time.locator('.insight-column').count()==55;assert time.locator('.insight-column-count').count()==0
      time.locator('select').select_option('1973');assert ('0件' if lang=='ja' else '0 shows') in time.locator('.insight-year-detail').inner_text()
      svg=time.locator('svg');svg.focus();p.keyboard.press('Home');assert svg.get_attribute('aria-valuenow')=='1972';p.keyboard.press('ArrowRight');assert svg.get_attribute('aria-valuenow')=='1973'
      box=svg.bounding_box();svg.tap(position=dict(x=box['width']/2,y=60));assert time.locator('.is-selected').count()==1
      labels=time.locator('svg .insight-axis').evaluate_all('(nodes)=>nodes.filter(e=>e.textContent.length===4&&Number(e.textContent)>1900).map(e=>{const r=e.getBoundingClientRect();return [r.left,r.right]})');assert all(labels[i][1]<=labels[i+1][0] for i in range(len(labels)-1)),labels
     if width==390:cat.screenshot(path=str(E/f'{name}-{lang}-donut.png'));time.screenshot(path=str(E/f'{name}-{lang}-yearly.png'))
     assert time.locator('.insight-name').evaluate_all('(nodes)=>nodes.every(e=>getComputedStyle(e).whiteSpace==="nowrap")')
     assert p.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,lang,name)
    root=area(p,'listening');rank=root.locator('[data-insight=score]');assert rank.locator('li').count()==15
    assert rank.locator('.rating-readout').evaluate_all('(nodes)=>new Set(nodes.map(e=>getComputedStyle(e).color)).size')==1
    rank.evaluate('(e)=>scrollTo(0,e.getBoundingClientRect().top+scrollY-80)');p.evaluate('window.keptArtist=document.querySelector("[data-insight=artists]");window.keptScoreHeading=document.querySelector("[data-insight=score] h3")')
    y=rank.locator('h3').bounding_box()['y'];rank.locator('select').select_option('2020');assert rank.locator('li').count()==1
    assert abs(rank.locator('h3').bounding_box()['y']-y)<3
    assert p.evaluate('keptArtist===document.querySelector("[data-insight=artists]")&&keptScoreHeading===document.querySelector("[data-insight=score] h3")')
    for value in ['2000','']:
     rank.locator('select').select_option(value);assert abs(rank.locator('h3').bounding_box()['y']-y)<3
    rank.get_by_role('button',name=more,exact=True).click();assert rank.locator('li').count()==30
    rank.get_by_role('button',name='折りたたむ' if lang=='ja' else 'Collapse',exact=True).click();assert rank.locator('li').count()==15;assert 0<=rank.locator('h3').bounding_box()['y']<150,(width,lang,rank.locator('h3').bounding_box(),p.evaluate('scrollY'));y=rank.locator('h3').bounding_box()['y']
    rank.get_by_role('button',name='鑑賞年' if lang=='ja' else 'Listening Year',exact=True).click();assert abs(rank.locator('h3').bounding_box()['y']-y)<3
    if width==390:rank.screenshot(path=str(E/f'score-{lang}.png'))
    # Settings changes may touch only the independent localStorage key.
    before=p.evaluate(SNAP);root.locator('.insight-settings').click();modal=p.locator('.insight-layout-modal');assert modal.locator('li').count()==7
    modal.locator('button[data-item=score][data-direction="-1"]').click();modal.locator('input[data-item=genre]').uncheck()
    if width==390:modal.screenshot(path=str(E/f'settings-{lang}.png'))
    modal.get_by_role('button',name='完了' if lang=='ja' else 'Done',exact=True).click();assert order(root)[0]=='score';assert 'genre' not in order(root);assert p.evaluate(SNAP)==before
    p.reload();p.evaluate('MLAReady');p.locator('#insights-screen').click();assert order(root)[0]=='score';assert 'genre' not in order(root)
    # Independent Collection settings and language-independent item IDs.
    other=area(p,'collection');assert order(other)[0]=='artists';root=area(p,'listening');p.locator('#ui-language').select_option('en' if lang=='ja' else 'ja');assert order(root)[0]=='score'
    root.locator('.insight-settings').click();modal=p.locator('.insight-layout-modal');modal.locator('input[type=checkbox]').evaluate_all('(nodes)=>nodes.forEach(e=>{if(e.checked)e.click()})');modal.get_by_role('button',name='Done' if lang=='ja' else '完了',exact=True).click();assert order(root)==[];assert root.locator('.insight-metrics').count()==1;assert p.locator('#export-json').is_visible()
    root.locator('.insight-settings').click();modal=p.locator('.insight-layout-modal');modal.get_by_role('button',name='Reset to Default' if lang=='ja' else '初期設定に戻す',exact=True).click();modal.get_by_role('button',name='Done' if lang=='ja' else '完了',exact=True).click();assert order(root)==['artists','score','genre','tags','label','time','release']
    assert not errors,errors;print('PASS',width,lang,'all chart forms; month paging/stable scale; 55 years/tap/keyboard/zero; score scroll anchors; settings/order/hide/reset/reload/independence/no IDB writes',flush=True);ctx.close()
  # Long histories and single/short timelines: every bar remains in one SVG.
  ctx,p=context();root=area(p,'live')
  for years in [1,5,24,30,40,55]:
   for width in [320,375,390,393,430]:
    p.set_viewport_size(dict(width=width,height=844));p.evaluate('n=>MLAInsights.render(document.querySelector("#live-insights"),Array.from({length:n},(_,i)=>Array.from({length:i===0||i===n-1?1:i%7===0?0:i%6+1},()=>({date:String(2027-n+i)+"-05-01"}))).flat(),"live",false,new Date(2026,10,27))',years)
    time=root.locator('[data-insight=time]');time.get_by_role('button',name='Yearly',exact=True).click();assert time.locator('svg').count()==1;assert time.locator('.insight-column').count()==years
    if width==390 and years>=24:time.screenshot(path=str(E/f'live-{years}-years.png'))
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
  print('PASS 1/5/24/30/40/55 years at all five widths, single untruncated chart',flush=True)
  browser.close()
 server.shutdown()
if __name__=='__main__':main()

"""Synthetic Chromium evidence; baseline mode must run before changing index.html."""
import json, os, sys, threading, subprocess
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album
PREF='mma-ui-grid-display-v1'
EVIDENCE=ROOT/'docs/display-options-evidence'
EVIDENCE.mkdir(exist_ok=True)
seed=dict(version=3,listening=[],collection=[],live=[])
for area in ['listening','collection']:
    seed[area]=[{**album(t,label='Very long label records international, 別のレーベル',genre='Ambient, Electronic, ジャズ',tags=['夜','Long tag'],store='Very long record shop 東京',format='LP'), 'release':['2025','2025-02','2025-02-03'][i%3], 'rating':['8.6','','8.4','10','0','9'][i], 'artist':'長いアーティスト名 Artist with a very long name'} for i,t in enumerate(['短い','A very long album title 日本語とEnglish 混在するタイトル','Missing label','Four','Five','Six'])]
    seed[area][2]['label']=''

def main():
    baseline='--baseline' in sys.argv
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    measurements=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        for lang in ['ja','en']:
            ctx=browser.new_context(viewport=dict(width=390,height=844),has_touch=True)
            ctx.route('https://**/*',lambda r:r.abort())
            ctx.add_init_script("""window.dbWrites=0;window.failPreference=false;const original=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='my-music-archive-pilot-v03')window.dbWrites++;if(k==='mma-ui-grid-display-v1'&&window.failPreference)throw Error('quota');return original.call(this,k,v)}""")
            page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            if baseline:
                html=subprocess.check_output(['git','show','b6f6e435255f1af52a55fa3d75b4e2cd0c499d96:index.html']).decode()
                ctx.route(f'http://127.0.0.1:{server.server_port}/',lambda r:r.fulfill(body=html,content_type='text/html'))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.evaluate('([k,v,l])=>{localStorage.setItem(k,JSON.stringify(v));localStorage.setItem("mma-ui-language",l)}',[KEY,seed,lang]);page.reload()
            raw=page.evaluate('(k)=>localStorage.getItem(k)',KEY)
            for area in ['listening','collection']:
                page.locator(f'[data-section={area}]').click()
                page.locator('#sort-toggle').click();page.locator('#group').select_option('none');page.locator('#sort').select_option('release-desc')
                for width in [320,375,390,430,1280]:
                    page.set_viewport_size(dict(width=width,height=844))
                    page.locator('#archive-panel').screenshot(path=str(EVIDENCE/f'{"before" if baseline else "default"}-{area}-{lang}-{width}.png'))
                if baseline: continue
                page.locator('#display-options').click()
                page.locator('#display-reset').click()
                # Default shown selections follow sort; removing them enters explicit custom mode.
                for field in ['rating','release']:
                    page.locator(f'[data-display-field={field}]').uncheck()
                assert page.locator('.tile-slot').count()==0
                page.locator('#display-close').click()
                for width in [320,375,390,430,1280]:
                    page.set_viewport_size(dict(width=width,height=844))
                    page.locator('#archive-panel').screenshot(path=str(EVIDENCE/f'zero-{area}-{lang}-{width}.png'))
                page.locator('#display-options').click()
                for field in ['genre','label','rating']:
                    page.locator(f'[data-display-field={field}]').check()
                    assert page.locator('.tile-slot').count()==6*(['genre','label','rating'].index(field)+1)
                    if field!='rating':
                        page.locator('#display-close').click()
                        for width in [320,375,390,430,1280]:
                            page.set_viewport_size(dict(width=width,height=844))
                            page.locator('#archive-panel').screenshot(path=str(EVIDENCE/f'{field}-count-{area}-{lang}-{width}.png'))
                        page.locator('#display-options').click()
                assert page.locator('[data-display-field=tags]').is_disabled()
                page.locator('[data-move=up][data-field=rating]').click()
                page.locator('[data-move=up][data-field=rating]').click()
                assert page.locator('#display-selected [data-order-field]').evaluate_all('(ns)=>ns.map(n=>n.dataset.orderField)')==['rating','genre','label']
                page.locator('#display-close').click()
                for width in [320,375,390,430,1280]:
                    page.set_viewport_size(dict(width=width,height=844))
                    page.locator('#archive-panel').screenshot(path=str(EVIDENCE/f'score-first-{area}-{lang}-{width}.png'))
                page.locator('#display-options').click()
                page.locator('[data-move=down][data-field=rating]').click();page.locator('[data-move=down][data-field=rating]').click()
                page.locator('#display-close').click()
                page.reload();page.locator(f'[data-section={area}]').click()
                page.locator('#sort-toggle').click();page.locator('#group').select_option('none');page.locator('#sort').select_option('release-desc')
                for width in [320,375,390,430,1280]:
                    page.set_viewport_size(dict(width=width,height=844))
                    page.locator('#archive-panel').screenshot(path=str(EVIDENCE/f'custom-{area}-{lang}-{width}.png'))
                    result=page.locator('.album-tile').evaluate_all('''ns=>ns.map(n=>{const rect=e=>{if(!e)return {overflow:false};const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,overflow:e.scrollWidth>e.clientWidth}};return {card:rect(n),art:rect(n.querySelector('.art')),title:rect(n.querySelector('.title')),artist:rect(n.querySelector('.muted.small')),slots:[...n.querySelectorAll('.tile-slot')].map(rect),score:rect(n.querySelector('.rating-readout'))}})''')
                    for row in [result[:3],result[3:]] if width<541 else [result]:
                        for key in ['art','title','artist']:
                            assert max(r[key]['y'] for r in row)-min(r[key]['y'] for r in row)<1
                        for i in range(3): assert max(r['slots'][i]['y'] for r in row)-min(r['slots'][i]['y'] for r in row)<1
                    assert all(abs(r['art']['w']-r['art']['h'])<1 for r in result)
                    assert all(not r['card']['overflow'] and not r['score']['overflow'] for r in result)
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    box=page.locator('#display-options').bounding_box();assert box['width']>=44 and box['height']>=44
                    measurements.append(dict(area=area,lang=lang,width=width,cards=result))
                    page.locator('#display-options').click();page.locator('#display-modal .dialog').screenshot(path=str(EVIDENCE/f'modal-{area}-{lang}-{width}.png'));page.locator('#display-close').click()
                other='en' if lang=='ja' else 'ja'
                before=page.evaluate('(k)=>localStorage.getItem(k)',PREF)
                page.locator('#ui-language').select_option(other)
                assert page.evaluate('(k)=>localStorage.getItem(k)',PREF)==before
                page.locator('#ui-language').select_option(lang)
                page.locator('#list-tab').click();assert page.locator('.tile-slot').count()==0
                page.locator('#grid-tab').click();assert page.locator('.tile-slot').count()==18
                page.locator('#sort').select_option('date-asc');assert page.locator('.tile-slot').first.get_attribute('data-field')=='genre'
                assert page.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
                assert page.evaluate('dbWrites')==0
            if not baseline:
                page.locator('#display-options').click();page.evaluate('failPreference=true');page.locator('#display-reset').click();page.locator('[data-display-field=rating]').uncheck();page.locator('#display-close').click()
                assert page.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw and page.evaluate('dbWrites')==0
                page.evaluate('failPreference=false');page.evaluate('(k)=>localStorage.setItem(k,JSON.stringify({listening:["rating","rating","bogus","genre","label","date"],collection:["store"]}))',PREF);page.reload()
                assert page.locator('.tile-slot').count()==0 # invalid listening falls back to default
                page.locator('[data-section=live]').click();assert page.locator('#display-options').is_hidden()
            assert not errors,errors
            ctx.close()
        browser.close()
    (EVIDENCE/('baseline.json' if baseline else 'measurements.json')).write_text(json.dumps(measurements,ensure_ascii=False,indent=2))
    print('PASS', 'baseline' if baseline else 'display options', 'JA/EN × Listening/Collection × five widths; DB unchanged')
if __name__=='__main__': main()

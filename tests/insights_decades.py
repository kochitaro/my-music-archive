"""Synthetic-only decade layout, baseline comparison and screenshots (Chromium, not Safari).

Run: MLA_BEFORE=/path/to/base-checkout python -u tests/insights_decades.py
"""
import hashlib, json, os, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, QuietHandler, album

KEY='my-music-archive-photos-v1'
OUT=ROOT/'docs/decade-bars-evidence'
CASES={
    'single':['2021'],
    'multiple':['1999','2000','2020','2029','1980'],
    '12-decades':[str(1910+i*10) for i in range(12)],
    'skewed':['2020']*60+['2010']*3+['2000']*2+['1990']*3+['1970'],
    'equal':['1970','1980','1990'],
    'unknown':['',None,'2000-02-29'],
    'empty':[],
}

def seed(years):
    records=[dict(album('Synthetic '+str(i)),release=year,genre='Rock',label='Label',tags=['Tag'],format='LP') for i,year in enumerate(years)]
    return dict(version=3,legacyStamp='sha256-'+hashlib.sha256(b'[null,null]').hexdigest(),listening=records,collection=records if len(years)==12 else records[::2],live=[dict(entryId='live',title='Synthetic show',artists=['Artist A'],venue='Hall',date='2026-01-02')])

def main():
    OUT.mkdir(exist_ok=True)
    baseline=Path(os.environ['MLA_BEFORE'])
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    results=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width in [320,375,390,430,768,1280]:
            for lang in ['ja','en']:
                ctx=browser.new_context(viewport=dict(width=width,height=844),is_mobile=width<600,has_touch=width<600)
                ctx.route('https://**/*',lambda r:r.abort())
                page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                # Keep baseline JS separate so aggregation and unaffected DOM can be compared directly.
                source=(baseline/'insights.js').read_text().replace('root.MLAInsights=api','root.BeforeInsights=api')
                page.add_script_tag(content=source)
                for case,years in CASES.items():
                    data=seed(years)
                    page.evaluate('([k,d,l])=>{localStorage.setItem(k,JSON.stringify(d));localStorage.setItem("mma-ui-language",l)}',[KEY,data,lang]);page.reload()
                    page.evaluate('async()=>await MLAReady')
                    page.add_script_tag(content=source)
                    expect(page.locator('#tab-change')).to_be_hidden()
                    raw=page.evaluate('(k)=>localStorage.getItem(k)',KEY)
                    page.evaluate('''key=>{window.dbWrites=0;const orig=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k===key)window.dbWrites++;return orig.call(this,k,v)}}''',KEY)
                    for area in ['listening','collection']:
                        page.locator(f'[data-section={area}]').click();page.locator('#insights-screen').click()
                        root=page.locator(f'#{area}-insights');rel=root.locator('[data-insight=release]')
                        # Exact baseline DOM equality includes year bars, all other blocks, theme and spacing.
                        comparison=page.evaluate('''([d,a,ja])=>{const n=document.createElement('div');BeforeInsights.render(n,d,a,ja);return n.innerHTML===document.getElementById(a+'-insights').innerHTML}''',[data[area],area,lang=='ja'])
                        assert comparison,(width,lang,case,area,'yearly baseline DOM')
                        expected=page.evaluate('''([d,a])=>BeforeInsights.releaseRows(BeforeInsights.aggregate(d,a),true).sort((a,b)=>Number(b.name)-Number(a.name))''',[data[area],area])
                        rel.get_by_role('button',name='年代別' if lang=='ja' else 'By Decade',exact=True).click()
                        actual=rel.locator('.insight-bar').evaluate_all('''rows=>rows.map(r=>{const n=r.querySelector('.insight-name'),c=r.querySelector('.insight-count'),t=r.querySelector('.insight-track'),f=r.querySelector('.insight-fill');return {name:n.textContent,count:Number(c.textContent),percent:parseFloat(f.style.width),ratio:f.getBoundingClientRect().width/t.getBoundingClientRect().width,inside:[r,n,c,t,f].every(e=>{const b=e.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&e.scrollWidth<=e.clientWidth+1})}})''')
                        maximum=max([r['count'] for r in expected],default=1)
                        assert len(actual)==len(expected),(actual,expected)
                        for got,want in zip(actual,expected):
                            assert got['name']==want['name']+('年代' if lang=='ja' else 's')
                            assert got['count']==want['count'] and got['inside'],got
                            assert abs(got['percent']-want['count']/maximum*100)<0.0001,got
                            assert abs(got['ratio']-want['count']/maximum)<0.005,got
                        if not expected:assert rel.locator('.insight-note').count()==1
                        assert rel.locator('.insight-decades').count()==0
                        assert rel.evaluate('(e)=>e.scrollWidth<=e.clientWidth')
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                        if case in ['skewed','12-decades'] and (width in [320,390] or width==1280 and lang=='ja'):
                            rel.screenshot(path=str(OUT/f'after-{area}-{case}-{lang}-{width}.png'))
                            if width==390 and lang=='ja':page.screenshot(path=str(OUT/f'full-{area}-{case}-ja-390.png'),full_page=True)
                        # Switching screens and changing language retains the decade selection.
                        page.locator('#archive-screen').click();page.locator('#insights-screen').click()
                        expect(rel.get_by_role('button',name='年代別' if lang=='ja' else 'By Decade',exact=True)).to_have_attribute('aria-pressed','true')
                        other='en' if lang=='ja' else 'ja';page.locator('#ui-language').select_option(other)
                        expect(rel.get_by_role('button',name='年代別' if other=='ja' else 'By Decade',exact=True)).to_have_attribute('aria-pressed','true')
                        page.locator('#ui-language').select_option(lang)
                        page.locator('[data-section=live]').click()
                        page.locator(f'[data-section={area}]').click();page.locator('#insights-screen').click()
                        expect(rel.get_by_role('button',name='年代別' if lang=='ja' else 'By Decade',exact=True)).to_have_attribute('aria-pressed','true')
                        # Reset only mode before comparing next area/case with the baseline yearly DOM.
                        rel.get_by_role('button',name='年別' if lang=='ja' else 'Yearly',exact=True).click()
                        results.append(dict(width=width,language=lang,case=case,area=area,rows=actual))
                    page.locator('[data-section=live]').click();page.locator('#insights-screen').click()
                    assert page.evaluate('''([d,ja])=>{const n=document.createElement('div');BeforeInsights.render(n,d,'live',ja);return n.innerHTML===document.getElementById('live-insights').innerHTML}''',[data['live'],lang=='ja'])
                    assert page.evaluate('dbWrites')==0 and page.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
                assert not errors,errors
                print('PASS 7 cases x 2 areas; numeric counts/order/ratios/layout; baseline yearly/other/Live DOM; state/language; zero DB writes',width,lang,flush=True)
                ctx.close()
        # Same data/viewport/language captures of the old implementation.
        ctx=browser.new_context(viewport=dict(width=390,height=844));ctx.route('https://**/*',lambda r:r.abort())
        for name in ['insights.js','insights.css']:
            ctx.route('**/'+name+'*',lambda r,_request,n=name:r.fulfill(path=str(baseline/n)))
        page=ctx.new_page();page.goto(f'http://127.0.0.1:{server.server_port}')
        for case in ['skewed','12-decades']:
            page.evaluate('([k,d])=>{localStorage.setItem(k,JSON.stringify(d));localStorage.setItem("mma-ui-language","ja")}',[KEY,seed(CASES[case])]);page.reload()
            for area in ['listening','collection']:
                page.locator(f'[data-section={area}]').click();page.locator('#insights-screen').click()
                rel=page.locator(f'#{area}-insights [data-insight=release]')
                rel.get_by_role('button',name='年代別',exact=True).click()
                rel.screenshot(path=str(OUT/f'before-{area}-{case}-ja-390.png'))
                print('BASELINE',case,area,'scrollWidth/clientWidth',rel.locator('.insight-decades').evaluate('(e)=>[e.scrollWidth,e.clientWidth]'),flush=True)
        (OUT/'layout-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
        browser.close()
    server.shutdown()

if __name__=='__main__':main()

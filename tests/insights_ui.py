"""PR③ UI assertions and comparable synthetic Chromium screenshots (not Safari)."""
import json, os, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album

def assert_legend_layout(category):
    rows=category.locator('.insight-legend li').evaluate_all('''elements=>elements.map(row=>{
        const marker=row.querySelector('.insight-swatch'),name=row.querySelector('.insight-name'),value=row.querySelector('.insight-value');
        const r=row.getBoundingClientRect(),m=marker.getBoundingClientRect(),n=name.getBoundingClientRect(),v=value.getBoundingClientRect();
        return {name:name.textContent,markerLeft:m.left-row.getBoundingClientRect().left,
            markerGap:n.left-m.right,gap:v.left-n.right,right:r.right-v.right,top:Math.abs(n.top-v.top),
            nameOverflow:name.scrollWidth>name.clientWidth+1,valueOverflow:value.scrollWidth>value.clientWidth+1,
            wrap:getComputedStyle(value).whiteSpace,nameAlign:getComputedStyle(name).textAlign,valueAlign:getComputedStyle(value).textAlign,
            narrow:innerWidth<600,nameHeight:n.height,lineHeight:parseFloat(getComputedStyle(name).lineHeight)};
    })''')
    assert rows
    for row in rows:
        assert abs(row['markerLeft'])<1.5,row
        assert row['markerGap']>=11 and row['gap']>=11,row
        assert abs(row['right'])<1.5 and row['top']<1.5,row
        assert row['valueAlign']=='right' and row['nameAlign'] in ['start','left'],row
        assert not row['nameOverflow'] and not row['valueOverflow'] and row['wrap']=='nowrap',row
        if row['narrow'] and len(row['name'])>70:assert row['nameHeight']>row['lineHeight']*1.5,row

def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    evidence=Path(os.environ.get('MLA_INSIGHTS_EVIDENCE',str(ROOT/'docs/insights-ui-evidence')));evidence.mkdir(exist_ok=True)
    records=[dict(album('Record '+str(i)),artist=f'Artist {i:02}',genre='Electronic, Ambient' if i%2 else 'Electronic',tags=['Music','Shared'],label='4AD' if i%2 else 'Very long label 名称 '*8,store='タワーレコードオンライン '+('Long store ' * 8) if i%2 else 'Tower Records',format='CD' if i%2 else 'LP') for i in range(46)]
    records.append(dict(album('Missing'),artist='',genre=' ',tags=[],label='',store=' ',format=''))
    seed=dict(version=3,listening=records,collection=records,live=[dict(entryId=str(i),title='Show',artists=[f'Artist {i:02}'],venue='Kanadevia Hall' if i%2 else 'Very long venue '*8,date='2026-01-01') for i in range(31)])
    before=os.environ.get('MLA_BEFORE')
    phase='before' if before else 'after'
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width,lang in [(width,lang) for width in [320,375,390,430,1280] for lang in ['ja','en']]:
            ctx=browser.new_context(viewport=dict(width=width,height=844),is_mobile=width<600,has_touch=width<600)
            ctx.route('https://**/*',lambda r:r.abort())
            if before:
                for name in ['insights.js','insights.css']:
                    ctx.route('**/'+name+'*',lambda r,_request,n=name:r.fulfill(path=str(Path(before)/n)))
            page=ctx.new_page();page.goto(f'http://127.0.0.1:{server.server_port}')
            page.evaluate('([k,d,l])=>{localStorage.setItem(k,JSON.stringify(d));localStorage.setItem("mma-ui-language",l)}',[KEY,seed,lang]);page.reload()
            for area in ['listening','collection','live']:
                page.locator(f'[data-section={area}]').click();page.locator('#insights-screen').click()
                root=page.locator(f'#{area}-insights');artists=root.locator('[data-insight=artists]')
                if not before:
                    expect(artists.locator('h3')).to_have_text('アーティスト' if lang=='ja' else 'Artists')
                    assert artists.locator('li').count()==15
                    expected=page.evaluate('([d,a])=>MLAInsights.aggregate(d,a)',[seed[area],area])
                    for field,entries in expected['categories'].items():
                        cat=root.locator(f'[data-insight={field}]');total=sum(e['count'] for e in entries)
                        expect(cat.locator('.insight-center')).to_have_text(str(total))
                        assert total==(31 if area=='live' else (69 if field=='genre' else 92 if field=='tags' else 46))
                        expect(cat.locator('.insight-donut')).to_have_attribute('aria-hidden','true')
                        slices=entries[:10]
                        if len(entries)>10:slices=slices+[dict(name='その他' if lang=='ja' else 'Other',count=sum(e['count'] for e in entries[10:]))]
                        for i,row in enumerate(slices):
                            value=f"{row['count']}{'（' if lang=='ja' else ' ('}{row['count']/total*100:.1f}%{'）' if lang=='ja' else ')'}"
                            expect(cat.locator('.insight-value').nth(i)).to_have_text(value)
                            expect(cat.locator('.insight-legend .insight-name').nth(i)).to_have_text(row['name'])
                            swatch=cat.locator('.insight-swatch').nth(i).evaluate('(e)=>e.style.backgroundColor')
                            assert swatch in cat.locator('.insight-donut').evaluate('(e)=>e.style.background')
                        assert_legend_layout(cat)
                    assert root.locator('.insight-note').count()==0
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    # All block content, including long names and center text, fits its box.
                    assert root.locator('.insight-center, .insight-legend li').evaluate_all('(es)=>es.every(e=>e.scrollWidth<=e.clientWidth)')
                if width==390 or area=='listening':
                    page.screenshot(path=str(evidence/f'{phase}-{area}-{lang}-{width}.jpg'),full_page=True,type='jpeg',quality=75)
                if not before:
                    more='さらに表示' if lang=='ja' else 'Show more';collapse='折りたたむ' if lang=='ja' else 'Collapse'
                    artists.get_by_role('button',name=more,exact=True).click();assert artists.locator('li').count()==30
                    if width==390 and area=='listening':artists.screenshot(path=str(evidence/f'after-artists-expanded-{lang}.jpg'),type='jpeg',quality=75)
                    while artists.get_by_role('button',name=more,exact=True).count():artists.get_by_role('button',name=more,exact=True).click()
                    assert artists.locator('li').count()==len(expected['artists'])
                    assert [x.inner_text() for x in artists.locator('.insight-name').all()]==[f"{i+1}. {r['name']}" for i,r in enumerate(expected['artists'])]
                    assert [x.inner_text() for x in artists.locator('.insight-count').all()]==[str(r['count']) for r in expected['artists']]
                    artists.get_by_role('button',name=collapse,exact=True).click();assert artists.locator('li').count()==15
            print('PASS',phase,width,lang,flush=True);ctx.close()
        if not before:
            ctx=browser.new_context(viewport=dict(width=320,height=844));page=ctx.new_page();page.goto(f'http://127.0.0.1:{server.server_port}')
            # Render edge cases directly, without changing stored data.
            for size in [0,1,15]:
                for area in ['listening','collection','live']:
                    rows=seed[area][:size]
                    page.evaluate('([rows,area])=>{const n=document.createElement("div");n.id="test-ui";n.className="insights-panel";document.body.replaceChildren(n);MLAInsights.render(n,rows,area,true)}',[rows,area])
                    root=page.locator('#test-ui');assert root.locator('[data-insight=artists] button').count()==0
                    assert root.locator('[data-insight=artists] li').count()==size
                    assert root.locator('.insight-donut').count()==(0 if size==0 else (1 if area=='live' else (5 if area=='collection' else 3)))
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            for area,field,unit in [('listening','label','record'),('collection','store','record'),('live','venue','show')]:
                page.evaluate('([rows,area])=>MLAInsights.render(document.querySelector("#test-ui"),rows,area,false)',[seed[area][:1],area])
                expect(page.locator(f'[data-insight={field}] .insight-value')).to_have_text('1 (100.0%)')
            rows=[dict(records[0],artist=str(i),genre=f'Genre {i}, Shared') for i in range(25)]
            page.evaluate('(rows)=>MLAInsights.render(document.querySelector("#test-ui"),rows,"listening",true)',rows)
            cat=page.locator('[data-insight=genre]')
            expect(cat.locator('.insight-center strong')).to_have_text('50')
            assert cat.locator('.insight-legend li').count()==11
            expect(cat.locator('.insight-value').last).to_have_text('16（32.0%）')
            assert_legend_layout(cat)
            print('PASS empty/single/15 artists; compact legends; many categories/Other/assignment totals',flush=True)
        browser.close()
    server.shutdown()

if __name__=='__main__':main()

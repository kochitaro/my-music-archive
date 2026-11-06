"""Isolated synthetic Chromium mobile/touch tests; never real iPhone Safari."""
import json, threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album, open_filters, edit, save

def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    evidence=ROOT/'docs/insights-evidence';evidence.mkdir(exist_ok=True)
    records=[dict(album('Record '+str(i)),artist=f'Artist {i:02}',genre=f'Genre {i:02}, Shared, shared',tags=[f'Tag {i:02}','Common','common'],label=f'Label {i:02}',store=f'Store {i:02}',format='CD' if i%2 else 'LP',date=f'{2000+i%27}-01-02',release=str(1980+i)) for i in range(46)]
    records[0]['artist']='Very long artist name '+('長い名称 ' * 25)
    seed=dict(version=3,listening=records,collection=records[:32],live=[dict(entryId=str(i),title='Show '+str(i),artists=[f'Artist {i:02}','Shared','shared',' '],venue=f'Venue {i:02}',date=f'{2000+i}-01-02') for i in range(25)])
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width in [320,375,390,430,1280]:
            for lang in ['ja','en']:
                ctx=browser.new_context(viewport=dict(width=width,height=844),is_mobile=width<600,has_touch=width<600)
                ctx.route('https://**/*',lambda r:r.abort())
                page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.clock.set_fixed_time(datetime(2026,11,6,tzinfo=timezone.utc))
                print('START',width,lang,flush=True)
                page.goto(f'http://127.0.0.1:{server.server_port}')
                page.evaluate('([k,d,l])=>{localStorage.setItem(k,JSON.stringify(d));localStorage.setItem("mma-ui-language",l)}',[KEY,seed,lang]);page.reload()
                raw=page.evaluate('(k)=>localStorage.getItem(k)',KEY)
                page.evaluate('''key=>{window.dbWrites=0;for(const method of ['setItem','removeItem','clear']){const original=Storage.prototype[method];Storage.prototype[method]=function(...args){if(method==='clear'||args[0]===key)window.dbWrites++;return original.apply(this,args)}}}''',KEY)
                def press(locator):
                    if width<600:locator.tap()
                    else:locator.click()
                for area in ['listening','collection','live']:
                    press(page.locator(f'[data-section={area}]'))
                    page.locator('#list-tab').click()
                    if area!='live':page.locator('#query').fill('retained query')
                    page.locator('#sort-toggle').click()
                    page.locator('#sort').select_option('rating-desc')
                    open_filters(page)
                    page.locator('#artist-filter').select_option('Shared' if area=='live' else 'Artist 01')
                    state=page.locator('#archive-content').evaluate('(e)=>[...e.querySelectorAll("select,input")].map(s=>[s.id,s.value])')
                    press(page.locator('#insights-screen'))
                    root=page.locator(f'#{area}-insights')
                    expect(root.locator('h2')).to_contain_text('統計' if lang=='ja' else 'Insights')
                    expect(root.locator('.insight-metrics strong').first).to_have_text(str(len(seed[area])))
                    assert root.locator('[data-insight=artists] li').count()==(26 if area=='live' else 30)
                    if width==390:page.screenshot(path=str(evidence/f'{area}-{lang}-pie-monthly.png'),full_page=True)
                    field='venue' if area=='live' else 'genre';cat=root.locator(f'[data-insight={field}]')
                    assert cat.locator('.insight-legend li').count()==11
                    press(cat.get_by_role('button',name='ランキング' if lang=='ja' else 'Ranking',exact=True))
                    assert cat.locator('li').count()==15
                    press(cat.get_by_role('button',name='さらに表示' if lang=='ja' else 'Show more',exact=True));assert cat.locator('li').count()==min(30,len(seed[area])+(area!='live'))
                    while cat.get_by_role('button',name='さらに表示' if lang=='ja' else 'Show more',exact=True).count():
                        press(cat.get_by_role('button',name='さらに表示' if lang=='ja' else 'Show more',exact=True))
                    press(cat.get_by_role('button',name='折りたたむ' if lang=='ja' else 'Collapse',exact=True));assert cat.locator('li').count()==15
                    if area!='live':assert root.locator('[data-insight=tags] .insight-donut').count()==1
                    time=root.locator('[data-insight=time]');assert time.locator('li').count()==12
                    assert time.locator('li').first.inner_text().startswith('2026-11')
                    press(time.get_by_role('button',name='さらに表示' if lang=='ja' else 'Show more',exact=True));assert time.locator('li').count()==24
                    press(time.get_by_role('button',name='年別' if lang=='ja' else 'Yearly',exact=True));assert time.locator('li').count()==5
                    press(time.get_by_role('button',name='さらに表示' if lang=='ja' else 'Show more',exact=True));assert time.locator('li').count()==10
                    press(time.get_by_role('button',name='月別' if lang=='ja' else 'Monthly',exact=True));assert time.locator('li').count()==12
                    press(time.get_by_role('button',name='年別' if lang=='ja' else 'Yearly',exact=True))
                    if area!='live':
                        rel=root.locator('[data-insight=release]');assert rel.locator('li').count()==10
                        press(rel.get_by_role('button',name='さらに表示' if lang=='ja' else 'Show more',exact=True));assert rel.locator('li').count()==20
                        press(rel.get_by_role('button',name='年代別' if lang=='ja' else 'By Decade',exact=True));assert rel.locator('.insight-decade').count()>=4
                    if width==390:page.screenshot(path=str(evidence/f'{area}-{lang}-ranking-yearly-decade.png'),full_page=True)
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(area,lang,width)
                    press(page.locator('#archive-screen'))
                    assert state==page.locator('#archive-content').evaluate('(e)=>[...e.querySelectorAll("select,input")].map(s=>[s.id,s.value])')
                    expect(page.locator('#list-tab')).to_have_attribute('aria-pressed','true')
                assert page.evaluate('dbWrites')==0
                assert page.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
                assert not errors,errors
                print('PASS bilingual/touch/layout/state/zero DB writes',width,lang,flush=True)
                ctx.close()
        # Real JSON restore refreshes visible Insights. Add/edit/delete verified via real forms in regression suites.
        ctx=browser.new_context();page=ctx.new_page();ctx.route('https://**/*',lambda r:r.abort())
        page.goto(f'http://127.0.0.1:{server.server_port}')
        page.locator('#insights-screen').click()
        assert page.locator('#listening-insights .insight-metrics strong').first.inner_text()=='0'
        assert page.locator('#listening-insights .insight-donut').count()==0
        page.on('dialog',lambda d:d.accept())
        page.locator('#import-json').set_input_files(dict(name='restore.json',mimeType='application/json',buffer=json.dumps(seed).encode()))
        expect(page.locator('#listening-insights .insight-metrics strong').first).to_have_text('46')
        # Language changes while Insights is open also rerender labels.
        page.locator('#ui-language').select_option('en');expect(page.locator('#listening-insights h2')).to_have_text('Listening Insights')
        page.locator('#ui-language').select_option('ja');expect(page.locator('#listening-insights h2')).to_have_text('リスニングの統計')
        print('PASS empty data, real JSON restore freshness, live language changes',flush=True)
        for area in ['listening','collection','live']:
            page.locator(f'[data-section={area}]').click()
            count=len(seed[area]);title='Fresh '+area
            if area=='live':
                page.locator('#add-live-trigger').click()
                page.locator('#live-title').fill(title)
                page.locator('#live-artists input').first.fill('00 Fresh')
                page.locator('#live-form > button').click()
                expect(page.locator('#live-create-modal')).not_to_have_class('modal open')
            else:
                page.locator('#manual-add-trigger').click()
                page.locator('#manual-title').fill(title);page.locator('#manual-artist').fill('00 Fresh')
                save(page)
            page.locator('#insights-screen').click()
            root=page.locator(f'#{area}-insights')
            expect(root.locator('.insight-metrics strong').first).to_have_text(str(count+1))
            expect(root.locator('[data-insight=artists]')).to_contain_text('00 Fresh')
            page.locator('#archive-screen').click();edit(page,title)
            page.locator('#e-live-artists input' if area=='live' else '#manual-artist').first.fill('00 Edited')
            save(page);page.locator('#insights-screen').click()
            expect(root.locator('[data-insight=artists]')).to_contain_text('00 Edited')
            expect(root.locator('[data-insight=artists]')).not_to_contain_text('00 Fresh')
            page.locator('#archive-screen').click();edit(page,title)
            page.locator('#delete').click();page.locator('#delete-accept').click()
            expect(page.locator('#modal')).not_to_have_class('modal open')
            page.locator('#insights-screen').click()
            expect(root.locator('.insight-metrics strong').first).to_have_text(str(count))
            expect(root.locator('[data-insight=artists]')).not_to_contain_text('00 Edited')
            print('PASS real create/edit/delete freshness',area,flush=True)

        browser.close()
    server.shutdown()
if __name__=='__main__':main()

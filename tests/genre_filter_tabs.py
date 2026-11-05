"""PR #18 review: genre filter visibility and independent tab state; no data writes."""
import os, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import KEY, QuietHandler, album, stored, choose, titles, unset_value, open_filters


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    seed=dict(version=3,
              listening=[album('L genre',genre='Ambient，Drone',tags=' Night, Night '),album('L unset',tags=['Keep'])],
              collection=[album('C genre',genre='Jazz',tags=[' Japan ', 'Japan']),album('C unset',tags=None)],
              live=[dict(entryId='live',title='Live unchanged',date='2026-01-02',memo='keep')])
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        for lang in ['ja','en']:
            context=browser.new_context(viewport=dict(width=390,height=844),is_mobile=True,has_touch=True)
            context.route('https://**/*',lambda r:r.abort())
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.evaluate('([k,v,l])=>{localStorage.setItem(k,JSON.stringify(v));localStorage.setItem("mma-ui-language",l)}',[KEY,seed,lang]);page.reload()
            raw=page.evaluate('(k)=>localStorage.getItem(k)',KEY)
            genre=page.locator('#genre-filter')

            def tab(area):
                page.locator(f'[data-section={area}]').click();open_filters(page)
                if area=='live':
                    expect(genre).to_be_hidden();expect(genre).to_be_disabled()
                    assert genre.evaluate('(e)=>e.hidden && getComputedStyle(e).display==="none"')
                    assert titles(page)==['Live unchanged']
                else:
                    expect(genre).to_be_visible();expect(genre).to_be_enabled()
                    assert not genre.evaluate('(e)=>e.hidden')

            tab('listening');choose(page,'genre','Drone');assert titles(page)==['L genre']
            tab('collection');choose(page,'genre',unset_value(page,'genre'));assert titles(page)==['C unset']
            # Open Live filters, redraw through list/grid/sort and switch language.
            for area in ['live','listening','live','collection','listening','collection','live']:
                tab(area)
                if area=='listening':
                    expect(genre).to_have_value('Drone');assert titles(page)==['L genre']
                elif area=='collection':
                    expect(page.locator('#genre-filter option:checked')).to_have_attribute('data-unset','true')
                    assert titles(page)==['C unset']
                else:
                    for control in ['#list-tab','#grid-tab']:
                        page.locator(control).click();expect(genre).to_be_hidden()
                    page.locator('#ui-language').select_option('en' if lang=='ja' else 'ja')
                    expect(genre).to_be_hidden();page.locator('#ui-language').select_option(lang)
                    page.locator('#sort-toggle').click();page.locator('#sort').select_option('date-asc')
                    open_filters(page);expect(genre).to_be_hidden()
            # Also retain a real value on Collection and unset on Listening.
            tab('collection');choose(page,'genre','Jazz');assert titles(page)==['C genre']
            tab('listening');choose(page,'genre',unset_value(page,'genre'));assert titles(page)==['L unset']
            tab('live');tab('collection');expect(genre).to_have_value('Jazz');assert titles(page)==['C genre']
            tab('listening');expect(page.locator('#genre-filter option:checked')).to_have_attribute('data-unset','true')
            assert titles(page)==['L unset']
            assert page.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw and stored(page)==seed
            assert not errors,errors
            print('PASS',lang,'Live hidden/disabled including filter panel, redraw and language switch; Listening/Collection visible/enabled; real/unset selections and results retained; saved DB raw unchanged',flush=True)
            context.close()
        browser.close()
    server.shutdown()

if __name__=='__main__':main()

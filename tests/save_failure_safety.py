"""Async discard refusal and archive-wide recovery boundaries, without unsaved JSON UI."""
import base64, json, os, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler
from data_preservation import seed_data, PHOTO, OLD


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    source=(ROOT/'index.html').read_text()
    seam="""window.safety={setSection,openEdit,saveDB,db:()=>db,draft:()=>draft,busy:()=>operationBusy,
    pause:()=>{resizePhoto=()=>new Promise((r,j)=>{window.finish=r;window.reject=j})}};"""
    source=source.replace("setSection('listening');showStorageState();",seam+"setSection('listening');showStorageState();")
    evidence=ROOT/'docs/simple-save-evidence'
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        for lang in ['ja','en']:
            ctx=browser.new_context(locale='ja-JP' if lang=='ja' else 'en-US',accept_downloads=True,viewport={'width':390,'height':844})
            ctx.route(base+'/',lambda r:r.fulfill(body=source,content_type='text/html'))
            ctx.route('https://**/*',lambda r:r.abort())
            ctx.add_init_script("const set=Storage.prototype.setItem;window.fail=false;Storage.prototype.setItem=function(k,v){if(window.fail&&k==='my-music-archive-pilot-v03')throw Error('INTERNAL_SECRET');return set.call(this,k,v)}")
            p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept());p.goto(base)
            def reset():
                p.evaluate('([k,o,d])=>{fail=false;localStorage.removeItem(o);localStorage.setItem(k,d)}',[KEY,OLD,json.dumps(seed_data())]);p.reload()
            for area in ['listening','collection','live']:
                reset();raw=p.evaluate('(k)=>localStorage.getItem(k)',KEY)
                p.evaluate('(a)=>{safety.setSection(a);safety.openEdit(a);safety.pause()}',area)
                photo='#e-live-photo' if area=='live' else '#album-photo'
                # Known validation is shown; a later unknown failure must replace that cause.
                title='#e-live-title' if area=='live' else '#manual-title'
                original_title=p.locator(title).input_value();p.locator(title).fill('')
                p.locator('#save').evaluate('e=>e.onclick()');p.wait_for_function('!safety.busy()')
                expect(p.locator('#save-notice-reason')).to_be_visible()
                p.locator('#save-return').click();p.locator(title).fill(original_title)
                p.locator('#memo').fill('Unsaved text')
                p.locator(photo).set_input_files(dict(name='keep.png',mimeType='image/png',buffer=base64.b64decode(PHOTO.split(',')[1])))
                p.locator('#save').evaluate('e=>{void e.onclick()}');p.wait_for_function('safety.busy()&&!!window.reject')
                p.locator('#save-again').evaluate('e=>e.onclick()');assert p.locator('#discard-input').is_hidden()
                p.evaluate("reject(Error('INTERNAL_SECRET'))");p.wait_for_function('!safety.busy()')
                expect(p.locator('#save-notice')).to_be_visible();expect(p.locator('#save-notice-reason')).to_be_hidden()
                assert 'INTERNAL_SECRET' not in p.locator('#save-notice').inner_text()
                assert p.locator(photo).evaluate('e=>e.files[0].name')=='keep.png'
                p.locator('#save-again').click();expect(p.locator('#discard-input')).to_be_visible();expect(p.locator('#save-notice')).to_be_hidden()
                # A callback starts another async save while confirmation was visible.
                p.locator('#save').evaluate('e=>{void e.onclick()}');p.wait_for_function('safety.busy()')
                old_url=p.url;p.locator('#discard-reload').evaluate('e=>e.onclick()')
                assert p.url==old_url and p.evaluate('safety.busy()')
                assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw and p.locator('#memo').input_value()=='Unsaved text'
                p.evaluate("reject(Error('INTERNAL_SECRET'))");p.wait_for_function('!safety.busy()')
                if p.locator('#discard-input').is_visible():p.locator('#discard-cancel').click()
                # Keep protection until explicit discard; DB bytes stay unchanged.
                p.locator('#close').click();expect(p.locator('#modal')).to_be_visible()
                p.locator('#save-again').click()
                with p.expect_navigation():p.locator('#discard-reload').click()
                assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
                print('PASS',lang,area,'photo failure retains File/draft; unknown reason hidden; async start/confirm discard refused; explicit discard only; DB unchanged',flush=True)
            reset();before=p.evaluate('(k)=>localStorage.getItem(k)',KEY)
            incoming=seed_data();incoming['live'][0]['memo']='backup restored'
            p.evaluate('fail=true')
            assert p.evaluate('(d)=>safety.saveDB(d,{kind:"restore"})',incoming) is False
            expect(p.locator('#save-notice')).to_be_visible()
            info=p.locator('#save-notice-info').inner_text()
            assert ('入力内容はこの画面' if lang=='ja' else 'Your input is still on this screen') not in info
            assert ('元ファイル' if lang=='ja' else 'original backup file') in info
            p.locator('#save-notice').screenshot(path=str(evidence/f'restore-failure-{lang}-390.png'))
            with p.expect_download() as dl:p.locator('#export-json').click()
            assert json.loads(Path(dl.value.path()).read_text())==json.loads(before)
            p.evaluate('fail=false');assert p.evaluate('(d)=>safety.saveDB(d,{kind:"restore"})',incoming)
            assert p.evaluate('(k)=>JSON.parse(localStorage.getItem(k))',KEY)==incoming
            assert p.evaluate('safety.draft()') is None
            print('PASS',lang,'failed restore keeps original-file guidance; saved archive backup intact; same valid backup retry settles draft',flush=True)
            for bad in ['{broken 日本語',json.dumps(dict(version=99,listening=[],collection=[],live=[]))]:
                p.evaluate('([k,v])=>localStorage.setItem(k,v)',[KEY,bad]);p.reload()
                expect(p.locator('#storage-state')).to_be_visible()
                with p.expect_download() as dl:p.locator('#recover-source').click()
                assert Path(dl.value.path()).read_text()==bad
                assert ('正常に復元できるとは限りません' if lang=='ja' else 'may not be restorable as-is') in p.locator('#recovery-info').inner_text()
                assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==bad
                if bad.startswith('{broken'):p.locator('#storage-state').screenshot(path=str(evidence/f'unreadable-{lang}-390.png'))
            print('PASS',lang,'unreadable/unsupported saved DB blocks writes, exact original recovery, no unconditional restoration claim',flush=True)
            assert not errors,errors
            ctx.close()
        browser.close()
    server.shutdown()

if __name__=='__main__':main()

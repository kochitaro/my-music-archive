"""Read-only bilingual guidance: exact copy, mobile geometry, real failed-save recovery."""
import json, os, re, subprocess, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler
from data_preservation import seed_data


def main():
    source=(ROOT/'index.html').read_text()
    # Recovery visibility now changes JavaScript; draft_visibility.py checks the exact permitted diff.
    assert re.findall(r'<details.*?</details>',source,re.S)==re.findall(r'<details.*?</details>',subprocess.check_output(['git','show','c7bffd4:index.html'],text=True),re.S),'guidance changed'
    copy=json.loads((ROOT/'tests/fixtures/backup-guide-copy.json').read_text())
    evidence=ROOT/'docs/backup-guide-evidence';evidence.mkdir(exist_ok=True)
    seam='window.guideTest={openEdit,setSection};'
    source=source.replace("setSection('listening');showStorageState();",seam+"setSection('listening');showStorageState();")
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        ctx=browser.new_context(viewport={'width':390,'height':844},locale='en-US',accept_downloads=True)
        ctx.route(base+'/',lambda r:r.fulfill(body=source,content_type='text/html'))
        ctx.route('https://**/*',lambda r:r.abort())
        ctx.add_init_script("const original=Storage.prototype.setItem;window.writes=[];window.failWrite=false;Storage.prototype.setItem=function(k,v){if(k==='my-music-archive-pilot-v03'&&failWrite)throw Error('synthetic quota');writes.push(k);return original.call(this,k,v)}")
        p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept());p.goto(base)
        p.evaluate('([k,v])=>localStorage.setItem(k,v)',[KEY,json.dumps(seed_data())]);p.reload()
        raw=p.evaluate('(k)=>localStorage.getItem(k)',KEY)
        assert not p.locator('#backup-guide').evaluate('(el)=>el.open')
        def language(lang):
            p.select_option('#ui-language',lang)
            expect(p.locator('html')).to_have_attribute('lang',lang)
        def exact(guide,lang,sections):
            actual=p.locator(f'{guide} > div[lang={lang}] > section').evaluate_all("els=>els.map(el=>[...el.children].map(n=>n.tagName==='OL'?[...n.children].map((li,i)=>(i+1)+'. '+li.textContent).join('\\n'):n.textContent).join('\\n\\n'))")
            assert actual==sections,(guide,lang)
        def geometry(guide):
            assert p.locator(guide).evaluate("el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&el.scrollWidth<=el.clientWidth}")
            assert p.locator(f'{guide} summary').evaluate('el=>el.getBoundingClientRect().height')>=44
        for lang in ['ja','en']:
            language(lang)
            exact('#backup-guide',lang,copy[lang]);exact('#recovery-guide',lang,[copy[lang][2]])
            # Native summary supports keyboard and exposes expanded state through details.
            summary=p.locator('#backup-guide summary');summary.focus();p.keyboard.press('Enter')
            assert p.locator('#backup-guide').evaluate('el=>el.open')
            for width in [320,375,390,430]:
                p.set_viewport_size({'width':width,'height':844})
                for area in ['listening','collection','live']:
                    p.evaluate('area=>guideTest.setSection(area)',area);geometry('#backup-guide')
                if width==390:
                    p.locator('#backup-guide').screenshot(path=str(evidence/f'backup-{lang}-390.png'))
            for _ in range(3):
                summary.focus();p.keyboard.press('Space');assert not p.locator('#backup-guide').evaluate('el=>el.open')
                p.keyboard.press('Space');assert p.locator('#backup-guide').evaluate('el=>el.open')
            # Language changes retain the open state and show only the chosen copy.
            language('en' if lang=='ja' else 'ja');assert p.locator('#backup-guide').evaluate('el=>el.open')
            expect(p.locator(f'#backup-guide > div[lang={lang}]')).to_be_hidden()
            language(lang);summary.focus();p.keyboard.press('Enter')
        assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
        assert set(p.evaluate('writes'))<= {'mma-ui-language'}
        print('PASS exact Japanese/English full copy; initial/repeated/keyboard toggle; language/open state; 24 mobile area/language/width layouts; zero DB writes',flush=True)
        p.set_viewport_size({'width':390,'height':844})
        for area in ['listening','collection','live']:
            p.evaluate('area=>{guideTest.setSection(area);guideTest.openEdit(area)}',area)
            p.locator('#memo').fill('Keep this unsaved input / 未保存を維持')
            p.evaluate('failWrite=true');p.locator('#save').evaluate('el=>el.onclick()')
            expect(p.locator('#unsaved-recovery')).to_be_visible()
            text=p.locator('#draft-text').input_value()
            with p.expect_download() as dl:p.locator('#draft-export').click()
            before=open(dl.value.path()).read()
            for lang in ['ja','en']:
                # select outside modal through its actual change handler, without dismissing the modal
                p.locator('#ui-language').evaluate('(el,lang)=>{el.value=lang;el.dispatchEvent(new Event("change",{bubbles:true}))}',lang)
                summary=p.locator('#recovery-guide summary');summary.focus();p.keyboard.press('Enter')
                assert p.locator('#recovery-guide').evaluate('el=>el.open')
                geometry('#recovery-guide')
                p.locator('#recovery-guide summary').scroll_into_view_if_needed()
                p.screenshot(path=str(evidence/f'recovery-{area}-{lang}-390.png'))
                p.locator(f'#recovery-guide > div[lang={lang}] p').last.scroll_into_view_if_needed()
                p.screenshot(path=str(evidence/f'recovery-{area}-{lang}-390-end.png'))
                assert p.locator('#draft-text').input_value()==text
                assert p.locator('#memo').input_value()=='Keep this unsaved input / 未保存を維持'
                summary.focus();p.keyboard.press('Enter')
            with p.expect_download() as dl:p.locator('#draft-export').click()
            assert open(dl.value.path()).read()==before==text
            p.locator('#close').click();expect(p.locator('#modal')).to_be_visible()
            assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
            p.locator('#draft-confirm').click();p.locator('#close').click();expect(p.locator('#modal')).to_be_hidden()
            p.evaluate('failWrite=false')
        assert not errors,errors
        print('PASS 3 areas failed-save recovery: direct guide, JA/EN, unchanged form/text/download bytes/DB, close blocked before confirmation and allowed after; no page errors',flush=True)
        browser.close()
    server.shutdown()

if __name__=='__main__':main()

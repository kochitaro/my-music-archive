"""Read-only bilingual guidance: exact copy, mobile geometry, real failed-save recovery."""
import json, os, re, subprocess, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler
from data_preservation import seed_data


def main():
    source=(ROOT/'index.html').read_text()
    # The archive backup/restore sections from PR #14 remain byte-identical.
    previous=subprocess.check_output(['git','show','f4d41ef:index.html'],text=True)
    for lang in ['ja','en']:
        def sections(doc):
            guide=doc[doc.index('id="backup-guide"'):]
            body=guide.split('<div lang="'+lang+'">',1)[1].split('</div>',1)[0]
            return re.findall(r'<section>.*?</section>',body,re.S)
        assert sections(source)[:2]==sections(previous)[:2]
    copy=json.loads((ROOT/'tests/fixtures/backup-guide-copy.json').read_text())
    evidence=ROOT/'docs/simple-save-evidence/guide';evidence.mkdir(parents=True,exist_ok=True)
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
            assert actual==sections,(guide,lang,[(i,a,b) for i,(a,b) in enumerate(zip(actual,sections)) if a!=b])
        def geometry(guide):
            assert p.locator(guide).evaluate("el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&el.scrollWidth<=el.clientWidth}")
            assert p.locator(f'{guide} summary').evaluate('el=>el.getBoundingClientRect().height')>=44
        for lang in ['ja','en']:
            language(lang)
            exact('#backup-guide',lang,copy[lang]);assert p.locator('#recovery-guide').count()==0
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
            expect(p.locator('#save-notice')).to_be_visible()
            before=p.locator('#memo').input_value()
            for lang in ['ja','en']:
                p.locator('#ui-language').evaluate('(el,lang)=>{el.value=lang;el.dispatchEvent(new Event("change",{bubbles:true}))}',lang)
                assert p.locator('#draft-text,#draft-export,#draft-confirm').count()==0
                assert p.locator('#memo').input_value()==before
            p.locator('#save-return').click();p.locator('#memo').select_text()
            p.locator('#close').click();expect(p.locator('#modal')).to_be_visible()
            assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
            # Complete the same form by retrying, without acknowledging recovery.
            p.evaluate('failWrite=false');p.locator('#save').click();expect(p.locator('#modal')).to_be_hidden()
            raw=p.evaluate('(k)=>localStorage.getItem(k)',KEY)
        assert not errors,errors
        print('PASS 3 areas failed-save: JA/EN, unchanged form/DB, no JSON UI, close blocked, whole-form retry settles draft; no page errors',flush=True)
        browser.close()
    server.shutdown()

if __name__=='__main__':main()

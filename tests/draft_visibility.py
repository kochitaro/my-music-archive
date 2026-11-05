"""Conditional recovery UI and baseline recovery-byte comparison; synthetic Chromium only."""
import json, os, subprocess, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler
from data_preservation import seed_data

BASE='c7bffd4843658855f680ab6bd0c23dff3a9892fe'

def main():
    baseline=subprocess.check_output(['git','show',BASE+':index.html'],text=True)
    current=(ROOT/'index.html').read_text()
    expected=baseline.replace('id="draft-open" type="button"','id="draft-open" type="button" hidden')
    expected=expected.replace(" const panel=$('unsaved-recovery');panel.hidden=!draft;if(!draft)return;"," const button=$('draft-open'),panel=$('unsaved-recovery');button.hidden=!pendingDraft();panel.hidden=!draft;if(!draft)return;")
    expected=expected.replace("if(dialog)dialog.append(panel);else $('storage-state').before(panel);","if(dialog)dialog.append(button,panel);else $('storage-state').before(button,panel);")
    expected=expected.replace("draftRecovered=true;$('unsaved-recovery').hidden=true","draftRecovered=true;$('draft-open').hidden=!pendingDraft();$('unsaved-recovery').hidden=true")
    assert current==expected,'unexpected application change outside visibility UI'
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    seam="window.v={setSection,openEdit,draft:()=>draft,recovered:()=>draftRecovered,busy:()=>operationBusy,fix:()=>{newId=()=> 'fixed-new-id';if(pendingRecord)pendingRecord.entryId='fixed-new-id'}};"
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        def run(source,area,kind,check):
            ctx=browser.new_context(locale='en-US',accept_downloads=True)
            ctx.route(base+'/',lambda r:r.fulfill(body=source.replace("setSection('listening');showStorageState();",seam+"setSection('listening');showStorageState();"),content_type='text/html'))
            ctx.route('https://**/*',lambda r:r.abort())
            ctx.add_init_script("const orig=Storage.prototype.setItem;window.fail=false;Storage.prototype.setItem=function(k,v){if(window.fail&&k==='my-music-archive-pilot-v03')throw Error('synthetic quota');return orig.call(this,k,v)};Date.prototype.toISOString=function(){return '2026-11-05T00:00:00.000Z'}")
            p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept());p.goto(base)
            button=p.locator('#draft-open')
            if check:expect(button).to_be_hidden()
            p.evaluate('([k,v])=>localStorage.setItem(k,v)',[KEY,json.dumps(seed_data())]);p.reload()
            p.evaluate('(a)=>v.setSection(a)',area)
            if check:
                expect(button).to_be_hidden()
                p.locator('#sort-toggle').click();p.locator('#sort').select_option('rating-desc');expect(button).to_be_hidden()
                p.locator('#filters-toggle').click();expect(button).to_be_hidden()
                options=p.locator('#artist-filter option').evaluate_all('els=>els.map(e=>e.value)')
                if area!='live' and len(options)>1:
                    p.locator('#artist-filter').select_option(options[1]);expect(button).to_be_hidden()
                    p.locator('#artist-filter').select_option('')
                if area!='live':
                    p.locator('#year-filter').fill('2026');expect(button).to_be_hidden()
                    p.locator('#year-filter').fill('')
                    p.locator('#query').fill('Example');p.locator('#search-form').evaluate('el=>el.requestSubmit()');expect(button).to_be_hidden()
            if kind=='edit':p.evaluate('(a)=>v.openEdit(a)',area)
            elif area=='live':p.locator('#add-live-trigger').click();p.locator('#live-title').fill('Unsaved Live')
            else:
                p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Unsaved Album');p.locator('#manual-artist').fill('Unsaved Artist')
            memo='#live-notes' if kind=='create' and area=='live' else '#memo'
            p.locator(memo).fill('Keep / 未保存')
            if check:expect(button).to_be_hidden()
            # Fixed IDs make new-entry recovery JSON comparable across profiles.
            p.evaluate("v.fix()")
            def save(fail):
                p.evaluate('(x)=>window.fail=x',fail)
                if kind=='create' and area=='live':p.locator('#live-form').evaluate('el=>el.requestSubmit()')
                else:p.locator('#save').evaluate('el=>el.onclick()')
                p.wait_for_function('!v.busy()')
            save(True);expect(p.locator('#unsaved-recovery')).to_be_visible()
            text=p.locator('#draft-text').input_value()
            with p.expect_download() as dl:p.locator('#draft-export').click()
            assert Path(dl.value.path()).read_text()==text
            if check:
                expect(button).to_be_visible();before=p.evaluate('JSON.stringify(v.draft())')
                p.locator('#draft-hide').click();expect(p.locator('#unsaved-recovery')).to_be_hidden()
                assert p.evaluate('JSON.stringify(v.draft())')==before
                button.click();expect(p.locator('#unsaved-recovery')).to_be_visible()
                assert p.locator('#draft-text').input_value()==text
                close='#close-live-create' if kind=='create' and area=='live' else '#close'
                p.locator(close).click();expect(p.locator('#unsaved-recovery')).to_be_visible()
                assert not p.evaluate('v.recovered()')
                p.locator('#draft-confirm').click();expect(button).to_be_hidden()
                assert p.evaluate('JSON.stringify(v.draft())')==before,'confirmation must retain draft'
                # New edits recapture the retained draft; successful retry settles it.
                p.locator(memo).fill('Retry current input');expect(button).to_be_visible()
                save(False);expect(button).to_be_hidden();assert p.evaluate('v.draft()') is None
            assert not errors,errors
            ctx.close()
            # New IDs for operation bookkeeping are intentionally nondeterministic.
            d=json.loads(text);return d
        for area in ['listening','collection','live']:
            for kind in ['edit','create']:
                old=run(baseline,area,kind,False);new=run(current,area,kind,True)
                assert old==new,(area,kind,old,new)
                print('PASS',area,kind,'visibility, real reopen, close protection, confirm, retry, baseline JSON/text/download equality',flush=True)
        browser.close()
    server.shutdown()

if __name__=='__main__':main()

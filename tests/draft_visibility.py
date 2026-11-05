"""Conditional recovery UI and baseline recovery-byte comparison; synthetic Chromium only."""
import json, os, subprocess, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler
from data_preservation import seed_data

BASE='0b3505a'  # PR #18: current independent genre/tag input baseline

def main():
    baseline=subprocess.check_output(['git','show',BASE+':index.html'],text=True)
    current=(ROOT/'index.html').read_text()
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
            if check:assert button.count()==0
            p.evaluate('([k,v])=>localStorage.setItem(k,v)',[KEY,json.dumps(seed_data())]);p.reload()
            p.evaluate('(a)=>v.setSection(a)',area)
            if check:
                assert button.count()==0
                p.locator('#sort-toggle').click();p.locator('#sort').select_option('rating-desc');assert button.count()==0
                p.locator('#filters-toggle').click();assert button.count()==0
                options=p.locator('#artist-filter option').evaluate_all('els=>els.map(e=>e.value)')
                if area!='live' and len(options)>1:
                    p.locator('#artist-filter').select_option(options[1]);assert button.count()==0
                    p.locator('#artist-filter').select_option('')
                if area!='live':
                    p.locator('#year-filter').select_option('2026');assert button.count()==0
                    p.locator('#year-filter').select_option('')
                    p.locator('#query').fill('Example');p.locator('#search-form').evaluate('el=>el.requestSubmit()');assert button.count()==0
            if kind=='edit':p.evaluate('(a)=>v.openEdit(a)',area)
            elif area=='live':p.locator('#add-live-trigger').click();p.locator('#live-title').fill('Unsaved Live')
            else:
                p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Unsaved Album');p.locator('#manual-artist').fill('Unsaved Artist')
            memo='#live-notes' if kind=='create' and area=='live' else '#memo'
            p.locator(memo).fill('Keep / 未保存')
            if check:assert button.count()==0
            # Fixed IDs make new-entry recovery JSON comparable across profiles.
            p.evaluate("v.fix()")
            def save(fail):
                p.evaluate('(x)=>window.fail=x',fail)
                if kind=='create' and area=='live':p.locator('#live-form').evaluate('el=>el.requestSubmit()')
                else:p.locator('#save').evaluate('el=>el.onclick()')
                p.wait_for_function('!v.busy()')
            save(True)
            if not check:
                text=p.evaluate('JSON.stringify(v.draft())')
            else:
                expect(p.locator('#save-notice')).to_be_visible();expect(p.locator('#save-notice-reason')).to_be_hidden()
                assert p.locator('#draft-open,#draft-text,#draft-export,#draft-confirm').count()==0
                text=p.evaluate('JSON.stringify(v.draft())');before=p.evaluate('JSON.stringify(v.draft())')
                p.locator('#save-return').click();assert p.evaluate('JSON.stringify(v.draft())')==before
                close='#close-live-create' if kind=='create' and area=='live' else '#close'
                p.locator(close).click();expect(p.locator('#save-notice')).to_be_visible();assert not p.evaluate('v.recovered()')
                p.locator('#save-again').click();expect(p.locator('#save-notice')).to_be_hidden();p.locator('#discard-cancel').click()
                assert p.evaluate('JSON.stringify(v.draft())')==before
                p.locator(memo).fill('Retry current input')
                save(False);assert p.evaluate('v.draft()') is None
            assert not errors,errors
            ctx.close()
            # New IDs for operation bookkeeping are intentionally nondeterministic.
            d=json.loads(text);return d
        for area in ['listening','collection','live']:
            for kind in ['edit','create']:
                old=run(baseline,area,kind,False);new=run(current,area,kind,True)
                # Unknown failure copy intentionally avoids claiming that no write occurred.
                old.pop('reason');new.pop('reason');assert old==new,(area,kind,old,new)
                print('PASS',area,kind,'no JSON UI, dismiss/cancel keeps protection, retry, baseline internal draft equality',flush=True)
        browser.close()
    server.shutdown()

if __name__=='__main__':main()

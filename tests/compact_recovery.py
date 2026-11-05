"""Compact recovery, explicit discard, bilingual mobile evidence. Synthetic Chromium."""
import json, os, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler
from data_preservation import seed_data


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    source=(ROOT/'index.html').read_text()
    seam="window.v={setSection,openEdit,draft:()=>draft,recovered:()=>draftRecovered,busy:()=>operationBusy,db:()=>db};"
    source=source.replace("setSection('listening');showStorageState();",seam+"setSection('listening');showStorageState();")
    evidence=ROOT/'docs/compact-recovery-evidence';evidence.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        for lang in ['ja','en']:
          for area in ['listening','collection','live']:
            for kind in ['edit','create']:
              ctx=browser.new_context(locale='ja-JP' if lang=='ja' else 'en-US',viewport={'width':390,'height':844},accept_downloads=True)
              ctx.route(base+'/',lambda r:r.fulfill(body=source,content_type='text/html'))
              ctx.route('https://**/*',lambda r:r.abort())
              p=ctx.new_page();errors=[];dialogs=[]
              p.on('pageerror',lambda e:errors.append(str(e)))
              p.on('dialog',lambda d:(dialogs.append(d.type),d.dismiss()))
              p.goto(base);p.evaluate('([k,v])=>localStorage.setItem(k,v)',[KEY,json.dumps(seed_data())]);p.reload()
              p.evaluate('(a)=>v.setSection(a)',area)
              if kind=='edit':p.evaluate('(a)=>v.openEdit(a)',area)
              elif area=='live':p.locator('#add-live-trigger').click();p.locator('#live-title').fill('Unsaved live')
              else:
                p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Unsaved album');p.locator('#manual-artist').fill('Artist')
              memo='#live-notes' if kind=='create' and area=='live' else '#memo'
              modal='#live-create-modal' if memo=='#live-notes' else '#modal'
              close='#close-live-create' if memo=='#live-notes' else '#close'
              p.locator(memo).fill('Keep this input / 未保存')
              # Real second-page write produces both storage-event and raw-string conflict.
              other=ctx.new_page();other.goto(base)
              other.evaluate('(k)=>{const d=JSON.parse(localStorage.getItem(k));d.listening[0].memo="Saved in another tab";localStorage.setItem(k,JSON.stringify(d))}',KEY)
              raw=other.evaluate('(k)=>localStorage.getItem(k)',KEY);other.close()
              def save():
                if memo=='#live-notes':p.locator('#live-form').evaluate('el=>el.requestSubmit()')
                else:p.locator('#save').evaluate('el=>el.onclick()')
                p.wait_for_function('!v.busy()')
              save()
              expect(p.locator('#save-notice')).to_be_visible();expect(p.locator('#unsaved-recovery')).to_be_hidden();expect(p.locator('#draft-text')).to_be_hidden()
              assert p.locator('#save-notice-title').inner_text()==('保存できませんでした' if lang=='ja' else 'Couldn’t Save Changes')
              assert p.locator('#save-notice-reason').inner_text()==('別のタブで記録が更新されています。' if lang=='ja' else 'The records were updated in another tab.')
              before=p.evaluate('JSON.stringify(v.draft())')
              if kind=='edit':
                for width in [320,375,390,430]:
                  p.set_viewport_size({'width':width,'height':844})
                  assert p.locator('#save-notice').evaluate('e=>e.scrollWidth<=e.clientWidth')
                  assert p.locator(modal+' .dialog').evaluate('e=>e.scrollWidth<=e.clientWidth')
                p.set_viewport_size({'width':390,'height':844});p.locator('#save-notice').screenshot(path=str(evidence/f'notice-{area}-{lang}-390.png'))
              p.locator('#save-return').click();expect(p.locator('#save-notice')).to_be_hidden()
              assert p.locator(memo).input_value()=='Keep this input / 未保存'
              assert p.evaluate('JSON.stringify(v.draft())')==before
              p.locator(close).click();expect(p.locator(modal)).to_be_visible();expect(p.locator('#save-notice')).to_be_visible()
              save();assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
              p.locator('#save-recover').click();expect(p.locator('#unsaved-recovery')).to_be_visible();expect(p.locator('#draft-text')).to_be_hidden()
              if kind=='edit':p.locator('#unsaved-recovery').screenshot(path=str(evidence/f'recovery-{area}-{lang}-390.png'))
              text=p.locator('#draft-text').input_value();assert json.loads(text)==p.evaluate('v.draft()')
              with p.expect_download() as dl:p.locator('#draft-export').click()
              assert Path(dl.value.path()).read_text()==text
              p.locator('#draft-json summary').click();expect(p.locator('#draft-text')).to_be_visible()
              p.locator('#draft-text').select_text();assert p.locator('#draft-text').evaluate('e=>e.selectionEnd-e.selectionStart')==len(text)
              # Failed download expands/selects the complete fallback text automatically.
              p.evaluate("()=>{window.savedCreateURL=URL.createObjectURL;URL.createObjectURL=()=>{throw Error('download unavailable')}}")
              p.locator('#draft-json summary').click();p.locator('#draft-export').click();expect(p.locator('#draft-text')).to_be_visible()
              assert p.locator('#draft-text').evaluate('e=>e.selectionEnd-e.selectionStart')==len(text)
              p.evaluate('()=>{URL.createObjectURL=savedCreateURL}')
              p.locator('#draft-hide').click();expect(p.locator('#unsaved-recovery')).to_be_hidden()
              assert not p.evaluate('v.recovered()')
              # beforeunload is still prevented after both dismiss operations.
              assert p.evaluate("()=>{const e=new Event('beforeunload',{cancelable:true});window.dispatchEvent(e);return e.defaultPrevented}")
              p.locator('#draft-discard').click();expect(p.locator('#discard-input')).to_be_visible()
              if kind=='edit':p.locator('#discard-input').screenshot(path=str(evidence/f'discard-{area}-{lang}-390.png'))
              latest=p.evaluate('JSON.stringify(v.draft())')
              p.locator('#discard-cancel').click();assert p.evaluate('JSON.stringify(v.draft())')==latest
              assert p.locator(memo).input_value()=='Keep this input / 未保存'
              p.locator('#draft-discard').click()
              with p.expect_navigation():p.locator('#discard-reload').click()
              assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
              assert p.evaluate('v.draft()') is None
              expect(p.locator(modal)).to_be_hidden()
              assert not dialogs,dialogs
              assert not errors,errors
              print('PASS',lang,area,kind,'compact notice, retained form/draft, real conflict retry refusal, JSON download/copy/fallback, close/unload guard, cancel/discard, unchanged saved DB',flush=True)
              ctx.close()
        browser.close()
    server.shutdown()

if __name__=='__main__':main()

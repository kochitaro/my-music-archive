"""Prime fresh unversioned browser caches, then verify versioned Insights assets load."""
import json, threading
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album

requests=[]
class Handler(QuietHandler):
    def do_GET(self):
        requests.append(self.path)
        path=urlsplit(self.path)
        if path.path=='/prime':
            body=b'<link rel="stylesheet" href="insights.css"><script src="insights.js"></script>'
            kind='text/html'
        elif not path.query and path.path=='/insights.js':
            body=b'window.staleInsightsAsset=true;';kind='text/javascript'
        elif not path.query and path.path=='/insights.css':
            body=b'body{--stale-insights-asset:1}';kind='text/css'
        else:
            return super().do_GET()
        self.send_response(200);self.send_header('Content-Type',kind)
        self.send_header('Cache-Control','public, max-age=86400')
        self.end_headers();self.wfile.write(body)

def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        context=browser.new_context(viewport=dict(width=390,height=844))
        page=context.new_page();page.goto(base+'/prime')
        assert page.evaluate('staleInsightsAsset')
        seed=dict(version=3,listening=[dict(album('Cached asset test'),genre='Electronic',label='4AD')],collection=[],live=[])
        raw=json.dumps(seed)
        page.evaluate('([k,d])=>{localStorage.setItem(k,d);localStorage.setItem("mma-ui-language","ja")}',[KEY,raw])
        page.goto(base+'/')
        assert page.evaluate('typeof MLAInsights.render')=='function'
        assert page.evaluate('typeof staleInsightsAsset')=='undefined'
        assert '/insights.js?v=20261109-multi-label' in requests
        assert '/insights.css?v=20261106-legend-layout-4' in requests
        page.locator('#insights-screen').click()
        root=page.locator('#listening-insights [data-insight=genre]')
        expect(root.locator('.insight-center')).to_have_text('1')
        expect(root.locator('.insight-value')).to_have_text('1（100.0%）')
        expect(root.locator('.insight-legend .insight-name')).to_have_text('Electronic')
        assert page.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
        print('PASS stale unversioned assets primed; versioned JS/CSS loaded; numeric center/compact legend; saved data unchanged')
        browser.close()
    server.shutdown()

if __name__=='__main__':main()

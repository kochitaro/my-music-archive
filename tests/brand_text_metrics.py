"""Read-only geometric assertions for the adopted T-6 wordmark."""
MEASURE="""e=>{const h=e.querySelector('h1'),r=h.getBoundingClientRect(),b=e.getBoundingClientRect(),n=document.querySelector('#sections').getBoundingClientRect(),s=getComputedStyle(h),bs=getComputedStyle(e);return {x:r.x,y:r.y,width:r.width,height:r.height,size:parseFloat(s.fontSize),weight:s.fontWeight,spacing:s.letterSpacing,lineHeight:s.lineHeight,color:s.color,font:s.fontFamily,bodyFont:getComputedStyle(document.body).fontFamily,brand:[b.x,b.y,b.width,b.height],sections:[n.x,n.y,n.width,n.height],margins:[parseFloat(bs.marginTop),parseFloat(bs.marginBottom)],gap:parseFloat(bs.gap),children:e.children.length,symbols:document.querySelectorAll('.brand svg,.brandmark,[data-brand-symbol]').length,overflow:h.scrollWidth>h.clientWidth+1||h.scrollHeight>h.clientHeight+1||r.right>innerWidth+.1||r.left<-.1,text:h.innerText,headingChildren:h.children.length,title:document.title,tabindex:h.getAttribute('tabindex')}}"""
def measure(page):return page.locator('.brand').evaluate(MEASURE)
def check(m,multiplier=1):
 size=22;assert abs(m['size']-size*multiplier)<.01,m
 assert m['text']=='My Listening Archive' and m['tabindex']=='-1' and m['headingChildren']==0,m
 assert m['title']=='My Listening Archive',m
 assert m['symbols']==0 and m['children']==1 and m['gap']==0,m
 assert not m['overflow'] and m['margins']==[5,16],m
 assert m['weight']=='400' and 'Josefin Sans' in m['font'] and 'Josefin' not in m['bodyFont'],m
 assert abs(float(m['spacing'].replace('px',''))-.02*m['size'])<.01,m
 assert abs(float(m['lineHeight'].replace('px',''))-1.25*m['size'])<.01,m
 assert m['color']=='rgb(240, 241, 243)',m
 if multiplier==1:assert abs(m['brand'][3]-40)<.01 and abs(m['height']-size*1.25)<.01,m
 else:assert m['brand'][3]>=40 and m['brand'][3]>=m['height']-.02,m
 assert abs(m['y']+m['height']/2-m['brand'][1]-m['brand'][3]/2)<.02,m
 assert abs(m['x']+m['width']/2-m['brand'][0]-m['brand'][2]/2)<.02,m

def accessible_heading(page):
 session=page.context.new_cdp_session(page)
 session.send('DOM.enable');session.send('Accessibility.enable')
 root=session.send('DOM.getDocument')['root']['nodeId']
 node=session.send('DOM.querySelector',{'nodeId':root,'selector':'#page-heading'})['nodeId']
 tree=session.send('Accessibility.getPartialAXTree',{'nodeId':node})['nodes']
 heading=next(n for n in tree if n.get('role',{}).get('value')=='heading')
 assert not heading['ignored'] and heading['name']['value']=='My Listening Archive',heading
 assert any(p['name']=='level' and p['value']['value']==1 for p in heading['properties']),heading
 session.detach()
 return {'role':'heading','level':1,'name':heading['name']['value']}

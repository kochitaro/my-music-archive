/* Presentation only: move the existing controls, keeping their handlers and values. */
globalThis.MLAArchiveToolbar = function ({japanese,getMode,view,closeSort,closeFilter,filterIds}) {
 const $=id=>document.getElementById(id);
 const bar=document.createElement('nav');bar.id='archive-toolbar';
 const inner=document.createElement('div');inner.className='archive-toolbar-inner';bar.append(inner);
 const toggle=document.createElement('button');toggle.id='archive-view-toggle';toggle.type='button';
 // Retain the original buttons and state for existing consumers, out of the tab order.
 const segments=$('grid-tab').parentElement;segments.hidden=true;segments.classList.add('hidden');
 inner.append(toggle,$('sort-toggle'),$('filters-toggle'),$('add-live-trigger'),segments);
 const panels=document.createElement('div');panels.id='archive-toolbar-panels';
 panels.append($('sort-wrap'),$('filters-wrap'));bar.prepend(panels);
 const handle=document.createElement('button');handle.id='archive-toolbar-handle';handle.type='button';
 handle.setAttribute('aria-controls','archive-toolbar-panels archive-toolbar-actions');
 inner.id='archive-toolbar-actions';bar.prepend(handle);document.body.append(bar);
 let collapsed=false;
 function syncPanels(){
  const open=!collapsed&&[ $('sort-wrap'),$('filters-wrap') ].some(el=>!el.classList.contains('hidden'));
  if(panels.hidden===open)panels.hidden=!open;
 }
 function setCollapsed(value){
  collapsed=value;closePanels();inner.inert=value;
  bar.classList.toggle('is-collapsed',value);document.body.classList.toggle('archive-toolbar-collapsed',value);
  sync();
 }
 handle.onclick=e=>{if(e.detail&&swiped){swiped=false;return}setCollapsed(!collapsed)};
 // Only this handle claims a vertical gesture; archive scroll/swipe listeners are untouched.
 let drag=null,swiped=false;
 handle.addEventListener('pointerdown',e=>{
  if(!e.isPrimary){drag=null;return}if(e.button!==0)return;
  swiped=false;drag={id:e.pointerId,x:e.clientX,y:e.clientY};handle.setPointerCapture(e.pointerId);
 });
 handle.addEventListener('pointerup',e=>{
  const start=drag;drag=null;if(!start||start.id!==e.pointerId)return;
  const dy=e.clientY-start.y,dx=e.clientX-start.x;
  if(Math.abs(dy)>=24&&Math.abs(dy)>Math.abs(dx)*1.5){swiped=true;setCollapsed(dy>0)}
  else if(Math.abs(dx)>=24)swiped=true;
 });
 handle.addEventListener('pointercancel',()=>{drag=null;swiped=false});
 document.querySelector('.archive-controls').remove();
 document.querySelector('.archive-actions').remove();
 document.querySelector('.filter-control').remove();
 toggle.onclick=()=>{view(getMode()==='grid'?'list':'grid');sync()};
 const close=document.createElement('button');close.type='button';close.className='toolbar-panel-close';panels.prepend(close);
 function closePanels(){closeSort();closeFilter();syncPanels()}
 close.onclick=()=>{const target=$('sort-toggle').getAttribute('aria-expanded')==='true'?$('sort-toggle'):$('filters-toggle');closePanels();target.focus()};
 bar.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panels.hidden){e.preventDefault();close.click()}});
 document.addEventListener('click',e=>{if(!bar.contains(e.target))closePanels()});
 for(const id of ['sort-toggle','filters-toggle'])$(id).addEventListener('click',e=>{
  sync();if(e.detail===0&&$(id).getAttribute('aria-expanded')==='true')close.focus({preventScroll:true});
 });
 function attr(el,key,value){if(el.getAttribute(key)!==value)el.setAttribute(key,value)}
 function content(el,value){if(el.textContent!==value)el.textContent=value}
 function sync(){
  const archive=!$('archive-content').hidden,modal=!!document.querySelector('.modal.open,[role="alertdialog"]:not([hidden])');
  if(bar.hidden!==(!archive||modal))bar.hidden=!archive||modal;
  document.body.classList.toggle('has-archive-toolbar',archive&&!modal);
  if(!archive||modal)closePanels();
  const ja=japanese(),grid=getMode()==='grid';
  attr(bar,'aria-label',ja?'アーカイブ操作':'Archive actions');
  content(toggle,(grid?'▦':'☰')+'\n'+(ja?(grid?'グリッド':'リスト'):(grid?'Grid':'List')));
  attr(toggle,'aria-label',(ja?'表示切替：':'Switch view: ')+(ja?(grid?'グリッド表示中':'リスト表示中'):(grid?'Grid selected':'List selected')));
  content(close,ja?'閉じる':'Close');
  attr(handle,'aria-label',collapsed?(ja?'操作バーを展開':'Expand action bar'):(ja?'操作バーを収納':'Collapse action bar'));
  attr(handle,'aria-expanded',String(!collapsed));
  content($('sort-toggle'),'↕\n'+(ja?'並べ替え':'Sort'));
  // Keep the original icon/label nodes used by the app's close/language handlers.
  const label=$('filter-label');content(label,ja?'絞り込み':'Filter');
  const active=filterIds.some(id=>!$(id+'-filter').classList.contains('hidden')&&$(id+'-filter').value!=='');
  $('filters-toggle').classList.toggle('has-filter',active);
  attr($('filters-toggle'),'aria-label',(ja?'絞り込み':'Filter')+(active?(ja?'：適用中':': active'):''));
  content($('add-live-trigger'),'＋\n'+(ja?'追加':'Add'));
  syncPanels();
 }
 // Existing rendering, section changes and dialogs remain the owners of their state.
 new MutationObserver(sync).observe(document.querySelector('main'),{subtree:true,attributes:true,attributeFilter:['class','hidden','aria-pressed']});
 for(const modal of document.querySelectorAll('.modal'))new MutationObserver(sync).observe(modal,{attributes:true,attributeFilter:['class']});
 new ResizeObserver(()=>{if(!bar.hidden)document.body.style.setProperty('--archive-toolbar-occupied',bar.getBoundingClientRect().height+'px')}).observe(bar);
 for(const id of ['sort-wrap','filters-wrap'])new MutationObserver(syncPanels).observe($(id),{attributes:true,attributeFilter:['class']});
 document.addEventListener('change',sync);sync();
};

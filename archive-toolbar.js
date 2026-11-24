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
 panels.append($('sort-wrap'),$('filters-wrap'));bar.prepend(panels);document.body.append(bar);
 document.querySelector('.archive-controls').remove();
 document.querySelector('.archive-actions').remove();
 document.querySelector('.filter-control').remove();
 toggle.onclick=()=>{view(getMode()==='grid'?'list':'grid');sync()};
 const close=document.createElement('button');close.type='button';close.className='toolbar-panel-close';panels.prepend(close);
 function closePanels(){closeSort();closeFilter()}
 close.onclick=()=>{const target=$('sort-toggle').getAttribute('aria-expanded')==='true'?$('sort-toggle'):$('filters-toggle');closePanels();target.focus()};
 bar.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();close.click()}});
 document.addEventListener('click',e=>{if(!bar.contains(e.target))closePanels()});
 for(const id of ['sort-toggle','filters-toggle'])$(id).addEventListener('click',()=>{
  sync();if($(id).getAttribute('aria-expanded')==='true')panels.querySelector('select:not(.hidden):not(:disabled)')?.focus({preventScroll:true});
 });
 function attr(el,key,value){if(el.getAttribute(key)!==value)el.setAttribute(key,value)}
 function content(el,value){if(el.textContent!==value)el.textContent=value}
 function sync(){
  const archive=!$('archive-content').hidden,modal=!!document.querySelector('.modal.open,[role="alertdialog"]:not([hidden])');
  if(bar.hidden!==(!archive||modal))bar.hidden=!archive||modal;
  document.body.classList.toggle('has-archive-toolbar',archive);
  if(!archive||modal)closePanels();
  const ja=japanese(),grid=getMode()==='grid';
  attr(bar,'aria-label',ja?'アーカイブ操作':'Archive actions');
  content(toggle,(grid?'▦':'☰')+'\n'+(ja?(grid?'グリッド':'リスト'):(grid?'Grid':'List')));
  attr(toggle,'aria-label',(ja?'表示切替：':'Switch view: ')+(ja?(grid?'グリッド表示中':'リスト表示中'):(grid?'Grid selected':'List selected')));
  content(close,ja?'閉じる':'Close');
  content($('sort-toggle'),'↕\n'+(ja?'並べ替え':'Sort'));
  // Keep the original icon/label nodes used by the app's close/language handlers.
  const label=$('filter-label');content(label,ja?'絞り込み':'Filter');
  const active=filterIds.some(id=>!$(id+'-filter').classList.contains('hidden')&&$(id+'-filter').value!=='');
  $('filters-toggle').classList.toggle('has-filter',active);
  attr($('filters-toggle'),'aria-label',(ja?'絞り込み':'Filter')+(active?(ja?'：適用中':': active'):''));
  content($('add-live-trigger'),'＋\n'+(ja?'追加':'Add'));
  const open=!$('sort-wrap').classList.contains('hidden')||!$('filters-wrap').classList.contains('hidden');
  panels.hidden=!open;
 }
 // Existing rendering, section changes and dialogs remain the owners of their state.
 new MutationObserver(sync).observe(document.querySelector('main'),{subtree:true,attributes:true,attributeFilter:['class','hidden','aria-pressed']});
 for(const modal of document.querySelectorAll('.modal'))new MutationObserver(sync).observe(modal,{attributes:true,attributeFilter:['class']});
 new ResizeObserver(()=>{if(!bar.hidden)document.body.style.setProperty('--archive-toolbar-occupied',bar.getBoundingClientRect().height+'px')}).observe(bar);
 document.addEventListener('change',sync);sync();
};

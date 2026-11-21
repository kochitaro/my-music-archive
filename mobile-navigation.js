/* UI gestures only; archive writes and section state remain owned by the app. */
globalThis.MLAMobileNavigation = function ({busy, unsaved, getSection, setSection, archiveVisible, japanese}) {
 const refresh = document.getElementById('reload-page');
 const top = document.getElementById('back-to-top');
 const archive = document.getElementById('archive-content');
 const modalOpen = () => !!document.querySelector('.modal.open,[role="alertdialog"]:not([hidden])');
 const blocked = () => busy() || unsaved() || modalOpen();
 function labels() {
  for (const [button, label] of [[refresh, japanese() ? 'ページを更新' : 'Reload page'], [top, japanese() ? 'ページ先頭へ戻る' : 'Back to top']]) {
   button.setAttribute('aria-label', label); button.title = label;
   if (button===refresh) button.textContent=label;
  }
  document.getElementById('page-actions-label').textContent=japanese()?'ページ操作':'Page actions';
 }
 labels(); document.getElementById('ui-language').addEventListener('change', labels);
 let reloading=false;
 function requestReload() {
  if (reloading) return;
  if (blocked()) {
   alert(busy()
    ? (japanese()?'保存・復元・回収などの処理中です。完了してから更新してください。':'Saving, restoring, or recovering is in progress. Wait for it to finish before reloading.')
    : (japanese()?'編集中の画面または未保存の入力があります。保存して画面を閉じてから更新してください。':'An editor or unsaved input is open. Save and close the dialog before reloading.'));
   return;
  }
  reloading=true;
  try { location.reload(); } catch (error) { reloading=false; throw error; }
 }
 refresh.addEventListener('click', requestReload);
 function updateTop() { const hidden=window.scrollY < 400 || modalOpen(); if (top.hidden!==hidden) top.hidden=hidden; }
 window.addEventListener('scroll', updateTop, {passive:true});
 new MutationObserver(updateTop).observe(document.body, {subtree:true, attributes:true, attributeFilter:['class','hidden']});
 top.addEventListener('click', () => {
  if (modalOpen()) return;
  window.scrollTo({top:0, behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
  // Keep keyboard/VoiceOver focus at the destination when this button disappears.
  document.getElementById('page-heading').focus({preventScroll:true});
 });
 updateTop();
 const controls = 'button,a,input,textarea,select,label,summary,[contenteditable]:not([contenteditable="false"]),[role="button"],[role="slider"],[role="textbox"],[tabindex],audio,video';
 function excluded(target) {
  if (!(target instanceof Element)) return true;
  // Only archive record buttons double as swipe surfaces. A nested control still
  // wins (rating/input/etc.), and search results or other buttons stay excluded.
  const card=target.closest('#library button.coverbtn,#library button.listrow');
  const control=target.closest(controls);
  if (control && control.id!=='page-heading' && (control!==card || card.disabled)) return true;
  for (let el=target; el && el!==document.body; el=el.parentElement) {
   if (el.scrollWidth > el.clientWidth + 1 && /auto|scroll/.test(getComputedStyle(el).overflowX)) return true;
  }
  return false;
 }
 let gesture=null, suppressUntil=0;
 window.addEventListener('pageshow', () => { reloading=false; });
 // Browser mode keeps its native refresh: install no custom pull listeners.
 const isStandalone=navigator.standalone===true || matchMedia('(display-mode: standalone)').matches;
 if (isStandalone) {
  // Standalone has no browser refresh UI to arbitrate with. Keep its bounce
  // native and observe moves, even after the browser makes them noncancelable.
  const indicator=document.getElementById('pull-refresh'),status=document.getElementById('pull-status');
  const TOP_SLOP=4,PULL_THRESHOLD=96;
  const atTop=()=>Math.max(0,window.scrollY)<=TOP_SLOP;
  let pull=null;
  function resetPull() {
   pull=null; indicator.hidden=true; indicator.removeAttribute('data-ready'); status.textContent='';
  }
  function innerScroller(target) {
   for (let el=target; el && el!==document.body && el!==document.documentElement; el=el.parentElement) {
    if (el.scrollHeight>el.clientHeight+1 && /auto|scroll/.test(getComputedStyle(el).overflowY)) return true;
   }
   return false;
  }
  function pullExcluded(target) {
   // A vertical pull may start over an ordinary button; taps and horizontal
   // swipe exclusions remain separate. Editors and their widgets stay native.
   if (!(target instanceof Element) || target.closest('input,textarea,select,label,[contenteditable]:not([contenteditable="false"]),[role="slider"],[role="spinbutton"],[role="textbox"],.rating-widget,audio,video')) return true;
   for (let el=target; el && el!==document.body; el=el.parentElement) {
    if (el.scrollWidth>el.clientWidth+1 && /auto|scroll/.test(getComputedStyle(el).overflowX)) return true;
   }
   return innerScroller(target);
  }
  const readyToRelease=p=>p.axis && p.distance>=PULL_THRESHOLD && atTop();
  function renderPull() {
   if (!pull) return;
   const ready=readyToRelease(pull),allowed=ready&&!blocked();
   indicator.hidden=!allowed; indicator.dataset.ready=String(allowed);
   const message=ready?(blocked()?(japanese()?'編集中または処理中のため更新できません':'Cannot reload while editing or processing'):(japanese()?'指を離して更新':'Release to reload')):'';
   if (status.textContent!==message) status.textContent=message;
  }
  document.addEventListener('touchstart', e => {
   resetPull(); suppressUntil=0;
   if (reloading || e.touches.length!==1 || !atTop() ||
       (window.visualViewport?.scale||1)>1.05 || pullExcluded(e.target)) return;
   const t=e.touches[0];
   // Edge starts are allowed for a vertical pull. Horizontal edge gestures never
   // get claimed here, and the archive swipe still reserves both edges for iOS.
   pull={id:t.identifier,x:t.clientX,y:t.clientY,axis:false,distance:0};
  }, {passive:true,capture:true});
  document.addEventListener('touchmove', e => {
   if (!pull) return;
   if (e.touches.length!==1 || e.touches[0].identifier!==pull.id) { resetPull(); return; }
   const t=e.touches[0],dx=t.clientX-pull.x,dy=t.clientY-pull.y;
   if (!pull.axis && Math.max(Math.abs(dx),Math.abs(dy))>=10) {
    if (dy<=0 || dy<Math.abs(dx)*1.5) { resetPull(); return; }
    pull.axis=true;
   }
   if (!pull.axis) return;
   pull.distance=Math.max(0,dy); suppressUntil=performance.now()+700;
   renderPull();
  }, {passive:true,capture:true});
  document.addEventListener('touchend', e => {
   const current=pull;
   const ended=[...e.changedTouches].find(t=>t.identifier===current?.id);
   if (!current || e.touches.length || !ended) { resetPull(); return; }
   current.distance=Math.max(0,ended.clientY-current.y);
   const ready=readyToRelease(current);
   resetPull();
   if (!ready) return;
   suppressUntil=performance.now()+700;
   requestReload();
  }, {passive:true,capture:true});
  window.addEventListener('scroll',renderPull,{passive:true});
  document.addEventListener('touchcancel', resetPull, {passive:true,capture:true});
  window.addEventListener('blur', resetPull);
  window.addEventListener('pagehide', resetPull);
  window.addEventListener('pageshow', resetPull);
 }
 archive.addEventListener('touchstart', e => {
  gesture=null; suppressUntil=0;
  if (e.touches.length!==1 || blocked() || !archiveVisible() || excluded(e.target)) return;
  const t=e.touches[0];
  // Leave both edges entirely to Safari / standalone system navigation.
  if (t.clientX < 32 || t.clientX > window.innerWidth-32) return;
  gesture={id:t.identifier,x:t.clientX,y:t.clientY,start:performance.now(),section:getSection(),axis:null,dx:0};
 }, {passive:true});
 archive.addEventListener('touchmove', e => {
  if (!gesture) return;
  if (e.touches.length!==1 || blocked() || !archiveVisible()) { gesture=null; return; }
  const t=e.touches[0];
  if (t.identifier!==gesture.id) { gesture=null; return; }
  const dx=t.clientX-gesture.x, dy=t.clientY-gesture.y;
  if (!gesture.axis && Math.max(Math.abs(dx),Math.abs(dy))>=10) {
   if (Math.abs(dx) < Math.abs(dy)*1.5) { gesture=null; return; }
   gesture.axis='x';
  }
  if (gesture.axis==='x') {
   if (!e.cancelable) { gesture=null; return; }
   e.preventDefault(); gesture.dx=dx;
   suppressUntil=performance.now()+700;
  }
 }, {passive:false});
 archive.addEventListener('touchend', e => {
  const g=gesture; gesture=null;
  if (!g || e.touches.length || ![...e.changedTouches].some(t=>t.identifier===g.id)) return;
  if (g.axis!=='x' || Math.abs(g.dx)<64 || performance.now()-g.start>1000 || blocked() || !archiveVisible() || getSection()!==g.section) return;
  const sections=['listening','collection','live'];
  const next=sections[sections.indexOf(g.section)+(g.dx<0?1:-1)];
  if (next) setSection(next);
  suppressUntil=performance.now()+700;
 }, {passive:true});
 archive.addEventListener('touchcancel', () => { gesture=null; }, {passive:true});
 window.addEventListener('blur', () => { gesture=null; });
 document.addEventListener('click', e => {
  // Keyboard / assistive technology clicks (detail=0) remain available.
  if (e.detail && performance.now()<suppressUntil) { e.preventDefault(); e.stopImmediatePropagation(); }
 }, true);
};

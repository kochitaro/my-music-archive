/* UI gestures only; archive writes and section state remain owned by the app. */
globalThis.MLAMobileNavigation = function ({busy, unsaved, getSection, setSection, archiveVisible, japanese}) {
 const refresh = document.getElementById('page-refresh');
 const top = document.getElementById('back-to-top');
 const archive = document.getElementById('archive-content');
 const modalOpen = () => !!document.querySelector('.modal.open,[role="alertdialog"]:not([hidden])');
 const blocked = () => busy() || unsaved() || modalOpen();
 function labels() {
  for (const [button, label] of [[refresh, japanese() ? 'ページを更新' : 'Reload page'], [top, japanese() ? 'ページ先頭へ戻る' : 'Back to top']]) {
   button.setAttribute('aria-label', label); button.title = label;
  }
 }
 labels(); document.getElementById('ui-language').addEventListener('change', labels);
 refresh.addEventListener('click', () => {
  // Refuse rather than risk interrupting a write, recovery, or an editor.
  if (blocked()) {
   alert(japanese() ? '編集中・未保存の入力、または処理中の操作があります。保存・処理の完了後、画面を閉じてから更新してください。' : 'An editor, unsaved input, or an operation is active. Finish saving or processing and close the dialog before reloading.');
   return;
  }
  location.reload();
 });
 function updateTop() { const hidden=window.scrollY < 400 || modalOpen(); if (top.hidden!==hidden) top.hidden=hidden; }
 window.addEventListener('scroll', updateTop, {passive:true});
 new MutationObserver(updateTop).observe(document.body, {subtree:true, attributes:true, attributeFilter:['class','hidden']});
 top.addEventListener('click', () => {
  if (modalOpen()) return;
  window.scrollTo({top:0, behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
  // Keep keyboard/VoiceOver focus at the destination when this button disappears.
  refresh.focus({preventScroll:true});
 });
 updateTop();
 const controls = 'button,a,input,textarea,select,label,summary,[contenteditable]:not([contenteditable="false"]),[role="button"],[role="slider"],[role="textbox"],[tabindex],audio,video';
 function excluded(target) {
  if (!(target instanceof Element)) return true;
  // Only archive record buttons double as swipe surfaces. A nested control still
  // wins (rating/input/etc.), and search results or other buttons stay excluded.
  const card=target.closest('#library button.coverbtn,#library button.listrow');
  const control=target.closest(controls);
  if (control && (control!==card || card.disabled)) return true;
  for (let el=target; el && el!==document.body; el=el.parentElement) {
   if (el.scrollWidth > el.clientWidth + 1 && /auto|scroll/.test(getComputedStyle(el).overflowX)) return true;
  }
  return false;
 }
 let gesture=null, suppressUntil=0;
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

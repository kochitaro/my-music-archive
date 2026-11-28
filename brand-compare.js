/* Temporary visual comparison only; no app state, storage, network or rendering hooks. */
(() => {
 'use strict';
 const preview = /^(?:deploy-preview|[a-f0-9]{8})\.my-listening-archive\.pages\.dev$/.test(location.hostname);
 const local = ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname);
 if (!(preview || local) || new URLSearchParams(location.search).get('logo-compare') !== '1') return;
 const brand = document.querySelector('.brand');
 if (!brand || !brand.querySelector('h1#page-heading')) return;
 const panel = document.createElement('aside');
 // Keep the app's outside-click handlers from changing open archive panels.
 panel.addEventListener('click', event => event.stopPropagation());
 panel.className = 'brand-comparison';
 panel.setAttribute('aria-label', 'ロゴ比較 / Logo comparison');
 const label = document.createElement('span');
 label.textContent = 'Logo';
 panel.append(label);
 for (const name of ['T-1', 'T-2', 'T-3', 'T-4', 'T-5', 'T-6']) {
  const button = document.createElement('button');
  button.type = 'button';
  button.textContent = name;
  button.setAttribute('aria-pressed', String(name === 'T-5'));
  // Pointer selection must not move focus/scroll away from the current screen.
  button.addEventListener('pointerdown', event => event.preventDefault());
  button.addEventListener('click', () => {
   // A private data attribute avoids the app's class/hidden/aria observers.
   const x = window.scrollX, y = window.scrollY;
   brand.dataset.brandChoice = name;
   for (const option of panel.querySelectorAll('button')) option.setAttribute('aria-pressed', String(option === button));
   // Enlarged text may wrap and trigger native scroll anchoring. Resolve the
   // header layout and preserve the current viewport before the next paint.
   brand.getBoundingClientRect();
   if (window.scrollX !== x || window.scrollY !== y) window.scrollTo({left:x, top:y, behavior:'instant'});
  });
  panel.append(button);
 }
 document.body.append(panel);
})();

/* Temporary visual comparison only; no app state, storage, network or rendering hooks. */
(() => {
 'use strict';
 const preview = /^(?:deploy-preview|[a-f0-9]{8})\.my-listening-archive\.pages\.dev$/.test(location.hostname);
 const local = ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname);
 if (!(preview || local) || new URLSearchParams(location.search).get('logo-compare') !== '1') return;
 const symbols = [...document.querySelectorAll('[data-brand-symbol]')];
 if (symbols.length !== 2) return;
 const mark = document.querySelector('.brandmark');
 const panel = document.createElement('aside');
 // Keep the app's outside-click handlers from changing open archive panels.
 panel.addEventListener('click', event => event.stopPropagation());
 panel.className = 'brand-comparison';
 panel.setAttribute('aria-label', 'ロゴ比較 / Logo comparison');
 const label = document.createElement('span');
 label.textContent = 'Logo';
 panel.append(label);
 for (const name of ['B-4', 'F-1']) {
  const button = document.createElement('button');
  button.type = 'button';
  button.textContent = name;
  button.setAttribute('aria-pressed', String(name === 'F-1'));
  // Pointer selection must not move focus/scroll away from the current screen.
  button.addEventListener('pointerdown', event => event.preventDefault());
  button.addEventListener('click', () => {
   // A private data attribute avoids the app's class/hidden/aria observers.
   mark.dataset.brandChoice = name;
   for (const option of panel.querySelectorAll('button')) option.setAttribute('aria-pressed', String(option === button));
  });
  panel.append(button);
 }
 document.body.append(panel);
})();

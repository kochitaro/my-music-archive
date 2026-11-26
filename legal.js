/* Legal documents never read or write archive storage. Both translations are in HTML. */
(()=>{'use strict';
 const languages=['ja','en'];
 const valid=value=>languages.includes(value)?value:null;
 function show(language){
  for(const code of languages)document.getElementById(code).hidden=code!==language;
  for(const link of document.querySelectorAll('[data-language]')){
   if(link.dataset.language===language)link.setAttribute('aria-current','true');
   else link.removeAttribute('aria-current');
  }
  document.documentElement.lang=language;
 }
 const initial=valid(location.hash.slice(1))||valid(new URLSearchParams(location.search).get('lang'))||((navigator.language||'').toLowerCase().startsWith('ja')?'ja':'en');
 show(initial);
 window.addEventListener('hashchange',()=>{const language=valid(location.hash.slice(1));if(language)show(language)});
})();

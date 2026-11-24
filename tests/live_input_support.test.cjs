const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('index.html','utf8');
function fn(name){const start=html.indexOf('function '+name+'(');return html.slice(start,html.indexOf('\n}',start)+2)}
test('tag-only Live edits omit untouched raw fields, including missing and partial dates',()=>{
 const input={'e-live-date':'','e-live-title':' Raw title ','e-live-venue':' Hall ','e-live-rating':'8.2',memo:'',performingArtists:[' Alpha ','Alpha']};
 const ctx={formBaseline:{input},formState:()=>({input:structuredClone(input)})};vm.createContext(ctx);vm.runInContext(fn('preserveUneditedLiveFields'),ctx);
 const update={date:'',title:'Raw title',venue:' Hall ',rating:'8.2',memo:'',artists:['Alpha','Alpha'],tags:['New']};
 ctx.preserveUneditedLiveFields(update);assert.deepEqual(update,{tags:['New']});
});
test('explicit Live changes remain updates while untouched fields are omitted',()=>{
 const input={'e-live-title':'Before',performingArtists:['Alpha']};
 const ctx={formBaseline:{input},formState:()=>({input:{...input,'e-live-title':'After',performingArtists:['Beta']}})};vm.createContext(ctx);vm.runInContext(fn('preserveUneditedLiveFields'),ctx);
 const update={title:'After',artists:['Beta'],memo:'',tags:[]};ctx.preserveUneditedLiveFields(update);
 assert.deepEqual(update,{title:'After',artists:['Beta'],tags:[]});
});

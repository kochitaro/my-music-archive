const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');
const source=fs.readFileSync('index.html','utf8');const start=source.indexOf("const DISPLAY_KEY=");const end=source.indexOf('function defaultDisplayFields',start);
function read(raw,fail=false){const ctx={$:()=>null,localStorage:{getItem(){if(fail)throw Error('blocked');return raw}}};vm.createContext(ctx);vm.runInContext(source.slice(start,end)+';globalThis.result=displayPreferences',ctx);return JSON.parse(JSON.stringify(ctx.result))}
test('empty custom preferences survive; archives validate independently',()=>{assert.deepEqual(read(JSON.stringify({listening:[],collection:['store','format','rating'],live:[]})),{listening:[],collection:['store','format','rating'],live:[]})});
for(const value of [null,{},'bad',['rating','rating'],['store'],['unsupported'],['rating','date','genre','label'],[1],['__proto__']])test('invalid preferences safely default: '+JSON.stringify(value),()=>{assert.equal(read(JSON.stringify({listening:value})).listening,null)});
test('corrupt JSON and read failure are contained',()=>{assert.deepEqual(read('{'),{listening:null,collection:null,live:[]});assert.deepEqual(read(null,true),{listening:null,collection:null,live:[]})});

test('legacy album preferences survive the Live extension',()=>{assert.deepEqual(read(JSON.stringify({listening:['rating','date'],collection:['label']})),{listening:['rating','date'],collection:['label'],live:[]})});
test('Live fields retain order without accepting album-only fields',()=>{assert.deepEqual(read(JSON.stringify({live:['artists','rating','memo']})).live,['artists','rating','memo']);assert.deepEqual(read(JSON.stringify({live:['release']})).live,[])});
for(const value of [null,{},['rating','rating'],['date','venue','artists','memo'],['bad']])test('invalid Live defaults safely '+JSON.stringify(value),()=>{assert.deepEqual(read(JSON.stringify({live:value})).live,[])});

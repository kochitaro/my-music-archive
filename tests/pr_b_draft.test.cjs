// Recovery settlement policy. Browser suite exercises the real forms, Files and Web Locks.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('index.html','utf8');
const source=html.slice(html.indexOf('function sameFiles('),html.indexOf('// One recovery owner'));
function setup(){
 const originalFile={name:'same.png'},form={input:{memo:'unsaved',rating:'9.0'},files:[],fileRefs:[originalFile]};
 const record={entryId:'row',title:'Album',artist:'A',memo:'unsaved',rating:'9.0'};
 const candidate={version:3,listening:[record],collection:[],live:[]};
 const token={session:1,form};
 const ctx={JSON,formOwner:{kind:'edit',area:'listening',id:'row'},formSession:1,activeOperation:token,
  currentForm:form,formBaseline:form,draft:{area:'listening',recordId:'row',operation:'edit',input:form.input,proposedRecord:{photo:'actual converted bytes'}},
  draftContext:{session:1,input:form.input,fileRefs:form.fileRefs},draftPhotoFiles:form.fileRefs,draftRecovered:false,
  operationBusy:true,saving:false,db:{version:3,listening:[],collection:[],live:[]},commits:0,alerts:[],captures:[],
  $:()=>({focus:()=>{}}),canSave:()=>true,isJapanese:()=>false,showDraft:()=>{},ArchiveValidationError:class extends Error{},SaveStopped:class extends Error{},validationMessage:e=>e.message};
 ctx.alert=x=>ctx.alerts.push(x);
 ctx.captureDraft=(op,reason,files)=>ctx.captures.push({op,reason,files,input:ctx.currentForm.input});
 ctx.commitDB=async v=>{ctx.commits++;ctx.db=JSON.parse(JSON.stringify(v))};
 ctx.stateFn=()=>ctx.currentForm;
 vm.createContext(ctx);vm.runInContext(source+';formState=stateFn;this.run=saveDB;this.compare=sameForm;',ctx);
 return {ctx,candidate,operation:{kind:'edit',area:'listening',id:'row',proposed:record,operationToken:token}};
}
test('same file name cannot substitute for actual selected File identity',()=>{
 const {ctx}=setup(),before=ctx.currentForm;
 assert.equal(ctx.compare(before,{...before,fileRefs:[{name:'same.png'}]}),false);
 assert.equal(ctx.compare(before,{...before,input:{memo:'changed',rating:'9.0'}}),false);
 assert.equal(ctx.compare(before,{...before}),true);
});
test('unrelated operation preserves draft bytes without a write',async()=>{
 const {ctx,candidate}=setup(),before=ctx.draft;ctx.operationBusy=false;
 assert.equal(await ctx.run(candidate,{kind:'edit',area:'collection',id:'other'}),false);
 assert.equal(ctx.commits,0);assert.equal(ctx.draft,before);assert.equal(ctx.captures.length,0);
});
test('only the current operation token can run during an asynchronous save',async()=>{
 const {ctx,candidate,operation}=setup(),before=ctx.draft;
 assert.equal(await ctx.run(candidate,{...operation,operationToken:{}}),false);
 assert.equal(ctx.commits,0);assert.equal(ctx.draft,before);assert.equal(ctx.captures.length,0);
});
test('exact whole-form retry settles only after actual persistence',async()=>{
 const {ctx,candidate,operation}=setup();
 assert.equal(await ctx.run(candidate,operation),true);
 assert.equal(ctx.commits,1);assert.equal(ctx.draft,null);assert.equal(ctx.db.listening[0].memo,'unsaved');
});
test('late input after save started remains recoverable despite a successful write',async()=>{
 const {ctx,candidate,operation}=setup();
 ctx.commitDB=async v=>{ctx.commits++;ctx.db=JSON.parse(JSON.stringify(v));ctx.currentForm={...ctx.currentForm,input:{memo:'late input',rating:'9.0'}}};
 assert.equal(await ctx.run(candidate,operation),false);
 assert.equal(ctx.db.listening[0].memo,'unsaved');assert.equal(ctx.captures[0].input.memo,'late input');
 assert.notEqual(ctx.draft,null);assert.equal(ctx.commits,1); // No rollback or closing authorization.
});
test('same failed restore can settle its own recovery',async()=>{
 const {ctx,candidate}=setup();ctx.draft.operation='restore';ctx.draftContext.restoreRaw=JSON.stringify(candidate);ctx.operationBusy=false;
 assert.equal(await ctx.run(candidate,{kind:'restore'}),true);assert.equal(ctx.draft,null);assert.equal(ctx.commits,1);
});
test('different restore cannot replace unacknowledged failed restore',async()=>{
 const {ctx,candidate}=setup(),before=ctx.draft;ctx.draft.operation='restore';ctx.draftContext.restoreRaw='different';ctx.operationBusy=false;
 assert.equal(await ctx.run(candidate,{kind:'restore'}),false);assert.equal(ctx.commits,0);assert.equal(ctx.draft,before);
});

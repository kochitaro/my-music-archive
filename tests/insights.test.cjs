const {test}=require('node:test');
const assert=require('node:assert/strict');
const I=require('../insights.js');
const rows=[{artist:' A ',genre:'Rock, rock, Jazz',tags:['X','x',' Y '],label:' Label ',store:' S ',format:'CD',date:'2026-11-06',release:'1999'}, {artist:'a',genre:'Jazz',tags:'Y, Z',label:'label',store:'S',format:'Digital',date:'2025',release:'2000-02-29'}, {artist:'B',date:'2024-02-29',release:'unknown'}, {artist:'  ',date:'2025-02-29',release:'0000'}, {}];
for(const area of ['listening','collection','live'])test(area+' independent totals and no mutation',()=>{const before=JSON.stringify(rows),s=I.aggregate(rows,area);assert.equal(s.total,5);assert.equal(s.artists.length,area==='live'?0:2);assert.equal(JSON.stringify(rows),before)});
test('classifications trim, fold case and deduplicate each record',()=>{const s=I.aggregate(rows,'collection');assert.deepEqual(s.categories.genre,[{name:'Jazz',count:2},{name:'Rock',count:1}]);assert.equal(s.categories.tags[0].count,2);for(const f of ['label','store'])assert.equal(s.categories[f][0].count,2);assert.deepEqual(s.categories.format.map(x=>x.name),['CD','Digital'])});
test('live artists count shows, never infer from title',()=>{const s=I.aggregate([{artists:['A',' A ','a','B',''],venue:'Tokyo'},{artists:['a','C'],venue:' Tokyo '},{title:'A'},{artists:[' ','']}],'live');assert.deepEqual(s.artists,[{name:'A',count:2},{name:'B',count:1},{name:'C',count:1}]);assert.equal(s.categories.venue[0].count,2)});
test('stable top 30, short and empty rankings',()=>{const r=Array.from({length:40},(_,i)=>({artist:'Artist '+String(i).padStart(2,'0')}));const s=I.aggregate(r,'listening');assert.equal(s.artists.slice(0,30).length,30);assert.equal(s.artists[0].name,'Artist 00');assert.equal(s.artists[29].name,'Artist 29');assert.equal(I.aggregate([],'live').artists.length,0)});
test('pie preserves sums and top fifteen across boundaries',()=>{
 for(const n of [0,1,10,15,16,100]){const entries=Array.from({length:n},(_,i)=>({name:String(i),count:n-i}));const result=I.pie(entries);assert.equal(result.length,Math.min(n,16));assert.equal(result.reduce((n,r)=>n+r.count,0),entries.reduce((n,r)=>n+r.count,0));assert.equal(result.filter(r=>r.other).length,n>15?1:0)}
});
test('strict date precision and leap boundaries',()=>{for(const d of ['',null,'bad','2026-00','2026-13','2025-02-29','1900-02-29','2026-04-31','0000','2026-01-00'])assert.equal(I.dateParts(d),null,d);for(const d of ['2026','2026-11','2024-02-29','2000-02-29'])assert.ok(I.dateParts(d),d)});
test('time includes year-only yearly, no invented January; periods and boundaries',()=>{const s=I.aggregate(rows,'listening');assert.equal(s.years.get(2025),1);assert.equal(s.months.get(2025*12),undefined);const now=new Date(2026,10,6);const m=I.timeline(s,'monthly',12,now);assert.equal(m.rows.length,12);assert.equal(m.rows[0].name,'2026-11');assert.equal(m.rows[0].count,1);assert.equal(m.rows[11].name,'2025-12');assert.equal(I.timeline(s,'monthly',24,now).rows.length,24);assert.equal(I.timeline(s,'yearly',5,now).rows.length,3);assert.equal(I.timeline(s,'monthly',12,new Date(2027,0,1)).rows[0].name,'2027-01')});
test('future and empty dates never become current; year pagination',()=>{const s=I.aggregate([{date:'2010'},{date:'2099-01-01'},{date:'invalid'}],'live');assert.equal(I.timeline(s,'yearly',5,new Date(2026,0,1)).rows[0].count,0);assert.equal(I.timeline(s,'yearly',10,new Date(2026,0,1)).rows.length,10);assert.equal(I.timeline(s,'monthly',12,new Date(2026,0,1)).rows.length,0)});
test('release year and decade boundaries; unknown excluded',()=>{const s=I.aggregate(rows,'collection');assert.deepEqual(I.releaseRows(s),[{name:'2000',count:1},{name:'1999',count:1}]);assert.deepEqual(I.releaseRows(s,true),[{name:'2000',count:1},{name:'1990',count:1}]);assert.equal(I.releaseRows(I.aggregate(Array.from({length:25},(_,i)=>({release:String(1980+i)})),'listening')).length,25)});

for(const area of ['listening','collection'])test(area+' decade cases: numeric descending, unchanged sums and immutable inputs',()=>{
 const cases=[
  ['single',['2021']],['multiple',['1999','2000','2020','2029','1980']],
  ['12 decades',Array.from({length:12},(_,i)=>String(1910+i*10))],
  ['skewed',[...Array(60).fill('2020'),...Array(3).fill('2010'),...Array(2).fill('2000'),...Array(3).fill('1990'),'1970']],
  ['equal',['1970','1980','1990']],['unknown',['','unknown',null,'0000','2025-02-29','2000-02-29']],
  ['empty',[]],['numeric not lexical',['0999','1000','2000']]
 ];
 for(const [name,years] of cases){
  const input=years.map(release=>Object.freeze({release}));Object.freeze(input);
  const stats=I.aggregate(input,area),expected=new Map();
  for(const [year,count] of stats.release){const decade=Math.floor(year/10)*10;expected.set(decade,(expected.get(decade)||0)+count)}
  const actual=I.releaseRows(stats,true);
  assert.deepEqual(actual,[...expected].sort((a,b)=>b[0]-a[0]).map(([year,count])=>({name:String(year),count})),name);
  assert.equal(actual.reduce((n,r)=>n+r.count,0),I.releaseRows(stats).reduce((n,r)=>n+r.count,0),name);
 }
});
test('area counts remain independent',()=>{
 assert.equal(I.releaseRows(I.aggregate([{release:'2020'},{release:'2021'}],'listening'),true)[0].count,2);
 assert.equal(I.releaseRows(I.aggregate([{release:'2020'}],'collection'),true)[0].count,1);
});

test('timeline excludes prehistory but retains gaps and empty states',()=>{
 const now=new Date(2026,10,27);
 for(const area of ['listening','collection','live']){
  const s=I.aggregate([{date:'2026-09-01'},{date:'2026-11-01'}],area),m=I.timeline(s,'monthly',12,now);
  assert.deepEqual(m.rows.map(r=>r.count),[1,0,1]);assert.equal(m.more,false);
  assert.deepEqual(I.timeline(I.aggregate([],area),'yearly',5,now).rows,[]);
  assert.deepEqual(I.timeline(I.aggregate([{date:'2099-01-01'}],area),'monthly',12,now).rows,[]);
  assert.deepEqual(I.timeline(I.aggregate([{date:'2024'},{date:'2026'}],area),'yearly',5,now).rows.map(r=>r.count),[1,0,1]);
 }
});
test('score ranking zero, unknown dates, ties, duplicate records and available years',()=>{
 const rows=[{title:'duplicate',rating:'0',date:'2026',release:''},{title:'duplicate',rating:'10',release:'2025'}, {title:'second',rating:'10',date:'2024',release:'2025'}, {rating:''},{rating:null},{rating:undefined},{rating:'8',release:'2020'}];
 const before=JSON.stringify(rows),all=I.scoreRanking(rows);
 assert.deepEqual(all.years,[2025,2020]);assert.deepEqual(all.rows.map(r=>r.rank),[1,1,3,4]);assert.deepEqual(all.rows.map(r=>r.score),[5,5,4,0]);assert.equal(all.rows[0].record,rows[1]);
 assert.equal(I.scoreRanking(rows,'release','2025').rows.length,2);assert.equal(I.scoreRanking(rows,'date','2026').rows[0].score,0);assert.deepEqual(I.scoreRanking(rows,'date').years,[2026,2024]);assert.equal(JSON.stringify(rows),before);
});

test('layout defaults, independent areas, unknown/duplicate IDs and future additions',()=>{
 assert.deepEqual(I.sectionIds('listening'),['artists','score','genre','tags','label','time','release']);
 assert.deepEqual(I.sectionIds('collection'),['artists','genre','tags','label','store','format','time','release']);
 assert.deepEqual(I.sectionIds('live'),['artists','score','venue','time']);
 for(const area of ['listening','collection','live'])for(const value of [null,{},[],{version:1,items:[{id:'time',visible:'false'}]}])assert.deepEqual(I.normalizeLayout(value,area),I.sectionIds(area).map(id=>({id,visible:true})));
 const value={version:1,items:[{id:'score',visible:false},{id:'obsolete',visible:true},{id:'score',visible:true},{id:'artists',visible:false}]};
 const result=I.normalizeLayout(value,'listening');assert.deepEqual(result.slice(0,2),[{id:'score',visible:false},{id:'artists',visible:false}]);assert.equal(result.length,7);assert.equal(result.at(-1).id,'release');
 assert.ok(result.slice(2).every(x=>x.visible));assert.equal(new Set(result.map(x=>x.id)).size,result.length);
 assert.ok(I.normalizeLayout({version:1,items:[]},'live').every(x=>x.visible));
});
test('monthly paging reaches record start; gaps and scale inputs remain intact',()=>{
 const s=I.aggregate([{date:'1986-03-01'},{date:'2026-11-01'}],'listening'),now=new Date(2026,10,27);
 assert.equal(I.timeline(s,'monthly',12,now).more,true);assert.equal(I.timeline(s,'monthly',24,now).rows.length,24);
 const all=I.timeline(s,'monthly',9999,now);assert.equal(all.rows.at(-1).name,'1986-03');assert.equal(all.more,false);assert.equal(all.rows.reduce((n,r)=>n+r.count,0),2);
});
test('live continuous months start at first dated month and retain gaps through now',()=>{
 const now=new Date(2026,10,27),s=I.aggregate([{date:'2024-05-01'},{date:'2026-11-01'},{date:'1980'},{date:'2099-01-01'}],'live');
 const rows=I.liveMonthRows(s,now);assert.equal(rows.length,31);assert.equal(rows[0].name,'2024-05');assert.equal(rows.at(-1).name,'2026-11');assert.equal(rows[1].count,0);assert.equal(rows.reduce((n,r)=>n+r.count,0),2);
 for(const records of [[],[{date:'2024'}],[{date:'2099-01-01'}]])assert.deepEqual(I.liveMonthRows(I.aggregate(records,'live'),now),[]);
});
test('period colors are stable identities, adjacent periods differ, palette cycles',()=>{
 for(const kind of ['year','decade','month']){const names=kind==='month'?['2025-12','2026-01','2026-02']:kind==='decade'?['1990','2000','2010']:['2024','2025','2026'];
  const colors=names.map(n=>I.columnColor(n,kind));assert.equal(new Set(colors).size,3);assert.ok(colors.every(c=>I.colors.includes(c)));assert.equal(I.columnColor(names[1],kind),colors[1]);
 }
 assert.equal(I.columnColor('2000'),I.columnColor('2015'));assert.equal(I.columnColor('1900','decade'),I.columnColor('2050','decade'));assert.equal(I.columnColor('2025-01','month'),I.columnColor('2026-04','month'));
});
test('existing Live layout gains score at end; reset defaults place score second',()=>{
 const items=[{id:'time',visible:true},{id:'artists',visible:false},{id:'venue',visible:false}];const value={version:1,items};const before=JSON.stringify(value);
 assert.deepEqual(I.normalizeLayout(value,'live'),[...items,{id:'score',visible:true}]);assert.equal(JSON.stringify(value),before);assert.equal(I.normalizeLayout(null,'live')[1].id,'score');
});
test('Live all-period score ranking preserves duplicates, zero, stable ties and unknown dates',()=>{
 const records=[{title:'Festival',rating:'10',date:''},{title:'Festival',rating:'10',date:'2026-01-01'},{title:'Zero',rating:'0'},{title:'Unrated',rating:''}];
 const ranked=I.scoreRanking(records,'date');assert.deepEqual(ranked.rows.map(r=>r.rank),[1,1,3]);assert.equal(ranked.rows[2].score,0);assert.equal(ranked.rows[0].record,records[0]);
});

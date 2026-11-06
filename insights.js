/* Read-only Insights. Inputs are never mutated; UI state exists only in memory. */
(function(root){
'use strict';
const clean=v=>typeof v==='string'?v.trim():'';
const key=v=>v.toLocaleLowerCase();
const genres=v=>clean(v).split(/[,，]/);
const tags=v=>Array.isArray(v)?v.filter(x=>typeof x==='string'):clean(v).split(',');
function counts(records,values){
 const map=new Map();
 for(const record of records){
  const seen=new Set();
  for(const value of values(record)){const name=clean(value),id=key(name);if(!name||seen.has(id))continue;seen.add(id);
   if(!map.has(id))map.set(id,{name,count:0});map.get(id).count++;
  }
 }
 return [...map.values()].sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name,'en',{sensitivity:'base'})||(a.name<b.name?-1:a.name>b.name?1:0));
}
function dateParts(value){
 const match=/^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/.exec(clean(value));if(!match)return null;
 const year=Number(match[1]),month=match[2]?Number(match[2]):null,day=match[3]?Number(match[3]):null;
 if(year<1||month!==null&&(month<1||month>12))return null;
 const leap=year%4===0&&(year%100!==0||year%400===0);
 if(day!==null&&(day<1||day>[31,leap?29:28,31,30,31,30,31,31,30,31,30,31][month-1]))return null;
 return {year,month};
}
function aggregate(records,area){
 const scalar=field=>r=>[r[field]];
 const artists=counts(records,area==='live'?r=>Array.isArray(r.artists)?r.artists:[]:scalar('artist'));
 const fields=area==='live'?['venue']:['genre','tags','label',...(area==='collection'?['store','format']:[])];
 const categories=Object.fromEntries(fields.map(field=>[field,counts(records,field==='genre'?r=>genres(r.genre):field==='tags'?r=>tags(r.tags):scalar(field))]));
 const months=new Map(),years=new Map(),release=new Map();
 const add=(map,k)=>map.set(k,(map.get(k)||0)+1);
 for(const record of records){const date=dateParts(record.date),rel=dateParts(record.release);
  if(date){add(years,date.year);if(date.month)add(months,date.year*12+date.month-1)}
  if(rel&&area!=='live')add(release,rel.year);
 }
 return {total:records.length,artists,categories,months,years,release};
}
function pie(entries){const result=entries.slice(0,10).map(x=>({...x}));if(entries.length>10)result.push({name:'',other:true,count:entries.slice(10).reduce((sum,x)=>sum+x.count,0)});return result}
function timeline(stats,mode,limit,now=new Date()){
 const monthly=mode==='monthly',current=monthly?now.getFullYear()*12+now.getMonth():now.getFullYear(),map=monthly?stats.months:stats.years;
 const earliest=Math.min(current,...map.keys());const step=monthly?12:5;
 const length=Math.min(limit,Math.max(step,current-earliest+1));
 const rows=Array.from({length},(_,i)=>{const k=current-i;return {name:monthly?String(Math.floor(k/12)).padStart(4,'0')+'-'+String(k%12+1).padStart(2,'0'):String(k),count:map.get(k)||0}});
 return {rows,more:length<current-earliest+1};
}
function releaseRows(stats,decades=false){const map=new Map();for(const [year,count] of stats.release){const k=decades?Math.floor(year/10)*10:year;map.set(k,(map.get(k)||0)+count)}return [...map].sort((a,b)=>decades?a[0]-b[0]:b[0]-a[0]).map(([year,count])=>({name:String(year),count}))}
const states=new Map();
// Every accepted save/restore replaces db with validated data (index.html commitDB).
// Weak keys release old snapshots and prevent stale counts after those replacements.
const snapshots=new WeakMap();
const colors=['#72cfee','#e5b66c','#b39bea','#77c5a4','#ed98ac','#92b5f7','#d2cc7d','#d89670','#77c6c8','#c3a7be','#8e9aaa'];
function render(container,records,area,ja,now=new Date()){
 let snapshot=snapshots.get(records);
 if(!snapshot||snapshot.area!==area){snapshot={area,stats:aggregate(records,area)};snapshots.set(records,snapshot)}
 const stats=snapshot.stats,t=(jp,en)=>ja?jp:en;
 const el=(tag,cls,value)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=value;return n};
 const state=(id,mode,limit)=>{const k=area+':'+id;if(!states.has(k))states.set(k,{mode,limit});return states.get(k)};
 const redraw=()=>render(container,records,area,ja,now);
 const button=(title,fn)=>{const b=el('button','btn alt',title);b.type='button';b.onclick=fn;return b};
 const block=(id,title)=>{const n=el('section','insight-block');n.dataset.insight=id;n.append(el('h3','',title));container.append(n);return n};
 const switches=(node,s,options,initial)=>{const group=el('div','insight-switch');group.setAttribute('role','group');group.setAttribute('aria-label',node.querySelector('h3').textContent);for(const [value,title] of options){const b=button(title,()=>{s.mode=value;s.limit=typeof initial==='function'?initial(value):initial;redraw()});b.setAttribute('aria-pressed',String(s.mode===value));group.append(b)}node.append(group)};
 const empty=node=>node.append(el('p','insight-note',t('集計できる登録データがありません。','No registered data to summarize.')));
 const bars=(node,rows,rank=false)=>{if(!rows.length){empty(node);return}const max=Math.max(1,...rows.map(x=>x.count));const list=el('ol','insight-bars');for(const [i,row] of rows.entries()){const li=el('li','insight-bar');li.append(el('span','insight-name',(rank?(i+1)+'. ':'')+row.name),el('span','insight-count',String(row.count)));const track=el('div','insight-track'),fill=el('div','insight-fill');fill.style.width=(row.count/max*100)+'%';track.append(fill);li.append(track);list.append(li)}node.append(list)};
 const paging=(node,s,total,step,more=s.limit<total)=>{const controls=el('div','insight-actions');if(more)controls.append(button(t('さらに表示','Show more'),()=>{s.limit+=step;redraw()}));if(s.limit>step)controls.append(button(t('折りたたむ','Collapse'),()=>{s.limit=step;redraw()}));node.append(controls)};
 container.replaceChildren();container.append(el('h2','',({listening:t('リスニング','Listening'),collection:t('コレクション','Collection'),live:t('ライブ','Live')})[area]+t('の統計',' Insights')));
 const metrics=el('div','insight-metrics');for(const [name,value] of [[area==='live'?t('ライブ公演数','Live shows'):area==='collection'?t('所有作品数','Owned records'):t('鑑賞作品数','Listening records'),stats.total],[area==='live'?t('観たアーティスト数','Artists seen'):t('アーティスト数','Artists'),stats.artists.length]]){const metric=el('div','');metric.append(el('strong','',String(value)),el('span','',name));metrics.append(metric)}container.append(metrics);
 container.append(el('p','insight-note',t('このアーカイブの全登録記録から集計します。再生回数ではありません。','Based on all saved records in this archive. These are not play counts.')));
 const artists=block('artists',t('アーティスト 上位30組','Top 30 artists'));artists.append(el('p','insight-note',t('件数順。同件数は名称順、順位は表示順の連番です。','By count, then name for ties. Ranks are sequential.')));artists.append(el('p','insight-note',area==='live'?t('出演公演数','Number of shows'):t('登録作品数','Number of records')));bars(artists,stats.artists.slice(0,30),true);
 const names={genre:t('ジャンル','Genres'),tags:t('タグ','Tags'),label:t('レーベル','Labels'),store:t('購入店舗','Stores'),format:t('フォーマット','Formats'),venue:t('会場','Venues')};
 for(const [field,entries] of Object.entries(stats.categories)){
  const node=block(field,names[field]),s=state(field,'pie',15);switches(node,s,[['pie',t('円グラフ','Pie Chart')],['ranking',t('ランキング','Ranking')]],15);
  if(field==='genre'||field==='tags')node.append(el('p','insight-note',t('割合は延べ分類件数に対する構成比です。1作品を複数分類に計上します。','Percentages use total category assignments. A record can count in multiple categories.')));
  if(!entries.length){empty(node);continue}
  if(s.mode==='ranking'){bars(node,entries.slice(0,s.limit));paging(node,s,entries.length,15);continue}
  const slices=pie(entries),total=entries.reduce((sum,x)=>sum+x.count,0);let offset=0;
  const donut=el('div','insight-donut');donut.setAttribute('aria-hidden','true');donut.style.background='conic-gradient('+slices.map((x,i)=>{const start=offset;offset+=x.count/total*100;return colors[i]+' '+start+'% '+offset+'%'}).join(',')+')';node.append(donut);
  const legend=el('ul','insight-legend');for(const [i,row] of slices.entries()){const li=el('li',''),swatch=el('span','insight-swatch');swatch.style.background=colors[i];li.append(swatch,el('span','insight-name',row.other?t('その他','Other'):row.name),el('span','',row.count+' · '+(row.count/total*100).toFixed(1)+'%'));legend.append(li)}node.append(legend);
 }
 const time=block('time',area==='live'?t('公演時期','Show dates'):area==='collection'?t('購入時期','Purchase dates'):t('鑑賞時期','Listening dates')),ts=state('time','monthly',12);
 switches(time,ts,[['monthly',t('月別','Monthly')],['yearly',t('年別','Yearly')]],value=>value==='monthly'?12:5);
 const period=timeline(stats,ts.mode,ts.limit,now);bars(time,period.rows);paging(time,ts,0,ts.mode==='monthly'?12:5,period.more);
 time.append(el('p','insight-note',t('未設定・不正な日付は除外。年のみの記録は年別に集計。現在より先の期間は表示しません。','Missing or invalid dates are excluded. Year-only dates count yearly. Future periods are not displayed.')));
 if(area!=='live'){
  const rel=block('release',t('リリース年','Release years')),rs=state('release','yearly',10);switches(rel,rs,[['yearly',t('年別','Yearly')],['decade',t('年代別','By Decade')]],10);
  const rows=releaseRows(stats,rs.mode==='decade');if(rs.mode==='yearly'){bars(rel,rows.slice(0,rs.limit));paging(rel,rs,rows.length,10)}else if(!rows.length)empty(rel);else{const chart=el('div','insight-decades');const max=Math.max(...rows.map(x=>x.count));for(const row of rows){const col=el('div','insight-decade');col.append(el('span','',String(row.count)));const track=el('div','insight-column'),fill=el('div','');fill.style.height=row.count/max*140+'px';track.append(fill);col.append(track,el('span','',row.name+t('年代','s')));chart.append(col)}rel.append(chart)}
  rel.append(el('p','insight-note',t('作品がリリースされた時代を表示します。鑑賞・購入時期とは異なります。発売年不明は除外。','The era of release, separate from listening or purchase dates. Unknown release years are excluded.')));
 }
}
const api={counts,dateParts,aggregate,pie,timeline,releaseRows,render};if(typeof module==='object'&&module.exports)module.exports=api;else root.MLAInsights=api;
})(globalThis);

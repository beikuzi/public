import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const d=JSON.parse(fs.readFileSync('dist/data.json'));
assert.equal(d.comments.length,0);
assert.equal(d.commentsStatus,'partial');
assert.equal(d.commentSummary.observedCount,3);
assert.equal(d.commentSummary.stancePercentage,null);
assert.equal(d.frames.length,4);
for(const f of d.frames)assert(fs.existsSync('dist/'+f.src));
const els=new Map();const el=s=>{if(!els.has(s))els.set(s,{innerHTML:'',classList:{add(){},remove(){}},showModal(){},close(){}});return els.get(s)};
const sandbox={document:{querySelector:el,querySelectorAll:()=>[],body:{}},window:{addEventListener(){}},location:{hash:'#/'},fetch:()=>new Promise(()=>{}),structuredClone,URL,setTimeout,console};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync('dist/app.js','utf8'),sandbox);
sandbox.injected=d;vm.runInContext('data=injected;original=structuredClone(data)',sandbox);
for(const route of ['','workbench','terminal','notebook','timeline']){
 sandbox.location.hash='#/'+route;vm.runInContext('render()',sandbox);
 const html=el('#app').innerHTML;
 assert(html.includes('id="main"'));
 assert(!html.includes('undefined'));
 if(route)assert(html.includes('真实案例 / Bilibili 匿名可见部分'));
 console.log('PASS route',route||'hub',html.length,'characters');
}
assert.equal(vm.runInContext('rows().length',sandbox),d.rows.length);
vm.runInContext("filter='blocked'",sandbox);assert(vm.runInContext("rows().every(r=>r.status==='blocked')",sandbox));
vm.runInContext("filter='all';sort='fast'",sandbox);assert(vm.runInContext('rows()[0].id',sandbox).startsWith('tiny-1-'));
vm.runInContext("scenario='preparation'",sandbox);assert.equal(vm.runInContext('rows()[0].id',sandbox),'caption');vm.runInContext("scenario='all'",sandbox);
assert.equal(vm.runInContext("safeLink('javascript:alert(1)')",sandbox),'#');
assert.equal(vm.runInContext("esc('<img onerror=alert(1)>')",sandbox),'&lt;img onerror=alert(1)&gt;');
assert.equal(d.rows.find(r=>r.id==='vosk').seconds,null);
assert.equal(d.rows.find(r=>r.id==='base').cer,null);
console.log('PASS data provenance, null handling, filters, timing sort, URL and HTML sanitization');

assert.equal(d.rows.find(r=>r.id==='sense-subway_eval-1').cer,0.6);
assert.equal(d.senseVoice.modelBytes,239233841);
assert(d.senseVoice.license.includes('custom'));
console.log('PASS independent SenseVoice metric and license checks');

assert.equal(d.visualEvidence.items.length,5);assert.equal(d.visualEvidence.items.filter(x=>x.status==='unanswerable').length,2);console.log('PASS five visual questions, including two explicit unanswerable cases');

vm.runInContext("scenario='subway-crop';stage='ASR'",sandbox);assert(vm.runInContext("rows().every(r=>r.scenario==='subway-crop'&&r.stage==='ASR')",sandbox));assert.equal(d.rows.find(r=>r.id==='sense-noise-speech_bandpass').cer,56/65);assert(d.rows.filter(r=>r.status==='documented').every(r=>r.seconds===null));console.log('PASS combined scenario/stage/status filters, noise data, paid latency null');
sandbox.legacy={schemaVersion:1,rows:[{id:'legacy',name:'Legacy row',status:'measured',stage:'ASR',seconds:1,cer:null,cost:0,currency:'USD'}]};sandbox.event={target:{files:[{size:100,text:async()=>JSON.stringify(sandbox.legacy)}],value:'legacy.json'}};await vm.runInContext('importJSON(event)',sandbox);assert.equal(vm.runInContext('scenarioKey(data.rows[0])',sandbox),'unassigned');assert.equal(vm.runInContext('scenario',sandbox),'all');assert(vm.runInContext('table()',sandbox).includes('不同场景，不能直接排名'));console.log('PASS legacy optional scenario import and unknown-scenario warning');

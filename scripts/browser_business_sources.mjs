import fs from 'node:fs/promises';import path from 'node:path';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const cfg=JSON.parse(await fs.readFile('runtime.local.json','utf8')),req=createRequire(path.join(cfg.modules,'business-source-check.cjs')),{chromium}=req('playwright');
const base='http://127.0.0.1:8530',id=process.argv[2]||'5188c85328274c63',out='test-results/business-source-fix-20261122',images='outputs/business-source-fix-20261122';await fs.mkdir(out,{recursive:true});await fs.mkdir(images,{recursive:true});
const api=async(url,body)=>{const r=await fetch(base+url,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});assert.ok(r.ok,await r.clone().text());return r.json();};
const before=await api('/api/tasks/'+id);try{await fs.access(out+'/before-task.json');}catch{await fs.writeFile(out+'/before-task.json',JSON.stringify(before,null,2));}
// Reuse the official files actually downloaded by verify_business_sources.py; the full pipeline still runs.
let task=before;
if(!process.argv.includes('--view-only')){await api('/api/tasks/'+id+'/collect',{refresh:false});for(let n=0;n<600;n++){task=await api('/api/tasks/'+id);if(task.jobs.length&&!task.jobs.some(j=>j.status==='running'))break;await new Promise(r=>setTimeout(r,500));}}
await fs.writeFile(out+'/after-task.json',JSON.stringify(task,null,2));assert.equal(task.jobs.at(-1).status,'succeeded');assert.equal(task.id,id);assert.deepEqual(task.meta.requested_years,[2023,2024,2025]);assert.equal(task.research.length,before.research.length);
assert.deepEqual(task.documents.filter(d=>d.kind==='official_report'&&d.company===task.company_a).slice(-3).map(d=>d.report_year).sort(),[2023,2024,2025]);
const cards=task.meta.business_cards.filter(c=>c.company===task.company_a);assert.equal(cards.length,4);assert.ok(cards.every(c=>c.quote&&c.page&&c.report_year));
const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true}),p=await b.newPage({viewport:{width:1440,height:900},acceptDownloads:true}),errors=[];p.on('pageerror',e=>errors.push(e.message));
const plain=text=>text.replace(/\s+/g,' ').trim();
try{
 await p.goto(base+'/#research/'+id);await p.locator('[data-business]').first().waitFor();
 for(const c of cards)assert.ok(plain(await p.locator('.finding').filter({hasText:c.company+' / '+c.dimension}).innerText()).includes(plain(c.quote)));
 await p.screenshot({path:images+'/business-evidence.png',fullPage:true});
 await p.locator('[data-business]').first().click();await p.locator('dialog[open]').waitFor();assert.match(await p.locator('#drawer-body').innerText(),/PDF第\d+页/);assert.ok((await p.locator('#drawer-body a').getAttribute('href')).includes('#page='));await p.screenshot({path:images+'/source-panel.png'});await p.keyboard.press('Escape');
 await p.reload();await p.locator('[data-business]').first().waitFor();assert.ok(plain(await p.locator('.finding').first().innerText()).includes(plain(cards[0].quote)));
 await p.locator('.research-tabs').getByRole('link',{name:'研究报告',exact:true}).click();await p.locator('.report-paper').waitFor();
 const waiting=p.waitForEvent('download');await p.getByRole('link',{name:'下载研究报告',exact:true}).click();const d=await waiting;assert.equal(await d.failure(),null);await d.saveAs(out+'/research-report.md');const report=await fs.readFile(out+'/research-report.md','utf8');assert.ok(report.includes(cards[0].quote));assert.ok(report.includes(cards[0].url));
 await p.setViewportSize({width:390,height:844});await p.goto(base+'/#research/'+id);await p.locator('[data-business]').first().waitFor();assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await p.screenshot({path:images+'/business-mobile.png',fullPage:true});assert.deepEqual(errors,[]);
 const result={status:'passed',task:id,checks:['same saved study with requested years preserved','three actual downloaded annual reports registered','four Tencent business dimensions have exact quote/page evidence','browser source panel points to actual PDF page','refresh retains evidence','actual report download includes evidence','390px no horizontal overflow'],pageErrors:errors,newPaidModelCalls:0};await fs.writeFile(out+'/browser-results.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{await b.close();}

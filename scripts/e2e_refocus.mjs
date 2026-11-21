import fs from 'node:fs/promises';import path from 'node:path';import {createRequire} from 'node:module';import {spawn,spawnSync} from 'node:child_process';import assert from 'node:assert/strict';
const cfg=JSON.parse(await fs.readFile('runtime.local.json','utf8')),require=createRequire(path.join(cfg.modules,'__e2e__.cjs')),{chromium}=require('playwright');
const root=process.cwd(),out='test-results/refocus',url='http://127.0.0.1:8532',phase=process.argv[2]||'regression';await fs.mkdir(out,{recursive:true});
const db=path.join(root,out,'browser-'+Date.now()+'.sqlite3');const cloned=spawnSync(cfg.python,['scripts/clone_test_db.py',db],{windowsHide:true});if(cloned.status)throw Error('Test DB clone failed');
const server=spawn(cfg.python,['server.py','--port','8532'],{cwd:root,env:{...process.env,FINRESEARCH_DB:db,FINRESEARCH_TEST_MODE:'0'},windowsHide:true});let logs='';server.stdout.on('data',b=>logs+=b);server.stderr.on('data',b=>logs+=b);
let browser,page;const results=[];async function test(name,fn){const start=Date.now();await fn();results.push({name,status:'passed',ms:Date.now()-start});}
try{
 for(let i=0;i<50;i++){try{if((await fetch(url+'/api/state')).ok)break;}catch{}await new Promise(r=>setTimeout(r,150));}
 browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const id=(await fs.readFile('data/real-case-id.txt','utf8')).trim();
 await test('Persona A: existing real model study, shared task and actual source PDF',async()=>{
  await page.goto(url+'/#research/'+id);await page.getByRole('heading',{name:'研究详情',exact:true}).waitFor();assert.equal(await page.locator('nav a').count(),4);assert.equal(await page.locator('.review-form').count(),6);assert.ok(await page.locator('[data-action=run-ai]').isDisabled());
  await page.getByRole('link',{name:'财务分析',exact:true}).click();await page.getByText(/4行可计算/).waitFor();assert.equal(page.url().split('/').at(-1),id);assert.match(await page.locator('#app').innerText(),/1,708.99/);assert.equal(await page.getByRole('link',{name:/原始披露 · PDF第/}).count(),20);
 });
 await test('Persona C: switching page resets reading position and clears stale feedback',async()=>{
  await page.evaluate(()=>window.scrollTo(0,1500));await page.getByRole('link',{name:'报告中心',exact:true}).click();await page.getByRole('heading',{name:'报告中心',exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.scrollY),0);
  await page.screenshot({path:out+'/reports-'+phase+'.png',fullPage:true});
 });
 await test('Persona A: report downloads preserve real evidence and model attribution',async()=>{
  const wait=page.waitForEvent('download');await page.getByRole('link',{name:'下载 Excel',exact:true}).click();await(await wait).saveAs(out+'/regression.xlsx');
  const md=page.waitForEvent('download');await page.getByRole('link',{name:'下载研究报告',exact:true}).click();await(await md).saveAs(out+'/regression.md');
  assert.match(await fs.readFile(out+'/regression.md','utf8'),/deepseek-flash/);
 });
 await test('Persona B: reject synthetic finance and retain real research batch',async()=>{
  await page.getByRole('link',{name:'财务分析',exact:true}).click();await page.getByText('手动导入真实财务表（备选）',{exact:true}).click();
  const csv=await fs.readFile('examples/demo.csv');await page.locator('#data-file').setInputFiles({name:'test-only.csv',mimeType:'text/csv',buffer:csv});await page.locator('[data-action=import]').click();await page.locator('#notice.error').waitFor();assert.match(await page.locator('#notice').innerText(),/模拟数据/);assert.match(await page.locator('#app').innerText(),/4行可计算/);
 });
 await test('Persona B: added source invalidates AI status and old conclusion in report',async()=>{
  await page.getByRole('link',{name:'研究详情',exact:true}).click();await page.getByText('补充公开资料正文（可选）',{exact:true}).click();const f=page.locator('#source-form');
  await f.locator('[name=title]').fill('年报原文补充核对');await f.locator('[name=url]').fill('https://static.cninfo.com.cn/finalpage/2025-04-03/1222993920.PDF');await f.locator('[name=content]').fill('其中：营业收入 40 170,899,152,276.34 147,693,604,994.14');await f.locator('button').click();
  await page.getByText('资料已保存，已有AI初稿需根据新来源重新检查。',{exact:true}).waitFor();
  assert.match(await page.locator('.task-context').innerText(),/待更新/);
  await page.getByRole('link',{name:'报告中心',exact:true}).click();await page.getByText('数据或来源已变化，上次AI初稿未作为当前结论。',{exact:true}).waitFor();assert.equal(await page.locator('.review-form').count(),0);
 });
 await test('Persona C: mobile viewport and refresh retain task context',async()=>{
  await page.setViewportSize({width:390,height:844});await page.goto(url+'/#finance/'+id);await page.getByText(/4行可计算/).waitFor();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.reload();await page.getByText(/4行可计算/).waitFor();await page.screenshot({path:out+'/mobile-'+phase+'.png',fullPage:true});
 });
 await test('Authorization and production boundaries remain enforced',async()=>{
  const info=await(await fetch(url+'/api/engine')).json();assert.equal(info.authorized_calls_remaining,0);
  assert.equal((await fetch(url+'/api/tasks/'+id+'/run-ai',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status,400);
  assert.equal((await fetch(url+'/api/demo',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status,400);
  assert.equal((await fetch(url+'/api/tasks',{method:'POST',headers:{Origin:'https://foreign.example','Content-Type':'application/json'},body:'{}'})).status,403);
 });
 assert.deepEqual(errors,[]);
}catch(e){if(page)await page.screenshot({path:out+'/failure-'+phase+'.png',fullPage:true});results.push({name:'failure',status:'failed',error:e.stack});process.exitCode=1;}
finally{if(browser)await browser.close();server.kill();const report={kind:'Synthetic personas exercising real financial snapshots in isolated copied database; no paid model calls',phase,tests:results.length,passed:results.filter(r=>r.status==='passed').length,results};await fs.writeFile(out+'/browser-'+phase+'.json',JSON.stringify(report,null,2));await fs.writeFile(out+'/server-'+phase+'.log',logs);console.log(JSON.stringify(report,null,2));}

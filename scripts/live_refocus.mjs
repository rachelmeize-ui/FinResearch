import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const cfg=JSON.parse(await fs.readFile('runtime.local.json','utf8'));
const require=createRequire(path.join(cfg.modules,'__live__.cjs'));
const {chromium}=require('playwright');
const url='http://127.0.0.1:8530',out='test-results/refocus';await fs.mkdir(out,{recursive:true});
const results=[];let browser,id;
async function test(name,fn){const start=Date.now();await fn();results.push({name,status:'passed',ms:Date.now()-start});await fs.writeFile(out+'/live-flow.json',JSON.stringify({kind:'Real external data + one authorized real model call',task_id:id,results},null,2));}
try{
 for(let i=0;i<50;i++){try{if((await fetch(url+'/api/state')).ok)break;}catch{}await new Promise(r=>setTimeout(r,150));}
 browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 await test('Homepage: four research pages and no development navigation',async()=>{
  await page.goto(url+'/#home');await page.getByRole('heading',{name:'金融研究，从可信资料开始。'}).waitFor();
  assert.deepEqual(await page.locator('nav a').allTextContents(),['研究首页','研究详情','财务分析','报告中心']);
  assert.equal(await page.getByRole('button',{name:'加载模拟案例'}).count(),0);
  await page.screenshot({path:out+'/home-before.png',fullPage:true});
 });
 await test('Create real-company research and retrieve real public annual statements',async()=>{
  await page.getByRole('button',{name:'新建研究',exact:true}).click();await page.locator('#new-form').waitFor();
  await page.locator('#new-form [name=question]').fill('比较2023—2024年度贵州茅台与五粮液收入增长、合并盈利能力和负债水平，说明数据口径差异与证据限制。');
  await page.locator('#new-form button').click();await page.getByRole('heading',{name:'研究详情',exact:true}).waitFor();
  id=page.url().split('/').at(-1);await fs.writeFile('data/real-case-id.txt',id);
  await page.locator('#job-panel').getByText('公开资料与财务分析已就绪',{exact:true}).waitFor({timeout:120000});
  const t=await (await fetch(url+'/api/tasks/'+id)).json();assert.equal(t.datasets.at(-1).rows.length,4);assert.equal(t.meta.collection.length,2);assert.ok(t.datasets.at(-1).rows.every(r=>r.data_kind!=='模拟数据'));
  assert.equal(t.datasets.at(-1).raw[1].net_profit,'89334728025.90');
  const res=await fetch(url+'/api/tasks/'+id+'/disclosures/600519.pdf');assert.equal(res.status,200);assert.ok((await res.arrayBuffer()).byteLength>3000000);
  await page.screenshot({path:out+'/research-before.png',fullPage:true});
 });
 await test('Financial analysis: shared task, real values, field evidence and calculation explanations',async()=>{
  await page.getByRole('link',{name:'财务分析',exact:true}).click();await page.getByRole('heading',{name:'财务分析',exact:true}).waitFor();assert.equal(page.url().split('/').at(-1),id);
  await page.getByText(/4行可计算/).waitFor();assert.match(await page.locator('#app').innerText(),/1,708.99/);assert.match(await page.locator('#app').innerText(),/15.71%/);
  assert.equal(await page.locator('svg.chart').count(),2);assert.equal(await page.getByRole('link',{name:/原始披露 · PDF第/}).count(),20);
  await page.getByText('指标计算口径与限制',{exact:true}).click();assert.match(await page.locator('#app').innerText(),/非归母净利润/);
  await page.screenshot({path:out+'/finance-before.png',fullPage:true});
 });
 await test('Real model research: one authorized completion, no synthetic fallback',async()=>{
  await page.getByRole('link',{name:'研究详情',exact:true}).click();await page.locator('[data-action=run-ai]').waitFor();
  const info=await (await fetch(url+'/api/engine')).json();assert.equal(info.authorized_calls_remaining,1);
  await page.locator('[data-action=run-ai]').click();
  await page.locator('#job-panel').getByText('真实模型研究完成',{exact:true}).waitFor({timeout:120000});
  const t=await (await fetch(url+'/api/tasks/'+id)).json();assert.equal(t.model_runs.length,1);assert.equal(t.model_runs[0].status,'succeeded');assert.equal(t.report.ai.cells.length,6);
  assert.ok(t.model_runs[0].usage.total_tokens>0);assert.ok(t.report.ai.cells.every(c=>c.status==='待核实'&&c.quote));
  assert.equal((await (await fetch(url+'/api/engine')).json()).authorized_calls_remaining,0);
  await fs.writeFile(out+'/real-model-result.json',JSON.stringify({task_id:id,model_run:t.model_runs[0],cells:t.report.ai.cells,sources:t.meta.collection},null,2));
  await page.screenshot({path:out+'/ai-before.png',fullPage:true});
 });
 await test('Report center: same task, actual downloads and source/model attribution',async()=>{
  await page.getByRole('link',{name:'报告中心',exact:true}).click();await page.getByRole('heading',{name:'报告中心',exact:true}).waitFor();assert.equal(page.url().split('/').at(-1),id);
  const dx=page.waitForEvent('download');await page.getByRole('link',{name:'下载 Excel',exact:true}).click();await(await dx).saveAs(out+'/real-research.xlsx');
  const dm=page.waitForEvent('download');await page.getByRole('link',{name:'下载研究报告',exact:true}).click();await(await dm).saveAs(out+'/real-research.md');
  const report=await fs.readFile(out+'/real-research.md','utf8');assert.match(report,/deepseek-flash/);assert.match(report,/https:\/\/static.cninfo.com.cn/);assert.match(report,/https:\/\/disc.static.szse.cn/);assert.match(report,/2023—2024/);assert.doesNotMatch(report,/example.invalid|人为构造/);
  await page.reload();await page.getByRole('heading',{name:'报告中心',exact:true}).waitFor();assert.match(await page.locator('#app').innerText(),/真实模型/);
  await page.screenshot({path:out+'/reports-before.png',fullPage:true});
 });
 assert.deepEqual(errors,[]);
}catch(e){results.push({name:'failure',status:'failed',error:e.stack});process.exitCode=1;}
finally{if(browser)await browser.close();const report={kind:'Real public annual reports + one authorized real model completion',task_id:id,tests:results.length,passed:results.filter(x=>x.status==='passed').length,results};await fs.writeFile(out+'/live-flow.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));}

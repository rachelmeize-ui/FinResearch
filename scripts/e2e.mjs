import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import http from 'node:http';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const cfg=JSON.parse(await fs.readFile(path.join(root,'runtime.local.json'),'utf8'));
const require=createRequire(path.join(cfg.modules,'__e2e__.cjs'));
const {chromium}=require('playwright');
const python=cfg.python||'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1118-904-0_26.1118.904.0_x64__3k8sg7r9htsxt/dependencies/python/python.exe';
const port=8532,url=`http://127.0.0.1:${port}`;
const out=path.join(root,'test-results');await fs.mkdir(out,{recursive:true});
const database=path.join(out,`e2e-${Date.now()}.sqlite3`);
let server,logs='',browser;
function start(){server=spawn(python,['server.py','--port',String(port)],{cwd:root,env:{...process.env,FINRESEARCH_DB:database,FINRESEARCH_ENABLE_AI:'0'},windowsHide:true});server.stdout.on('data',b=>logs+=b);server.stderr.on('data',b=>logs+=b);}
async function ready(){for(let i=0;i<60;i++){try{const r=await fetch(url+'/api/state');if(r.ok)return;}catch{}await new Promise(r=>setTimeout(r,150));}throw Error('server not ready: '+logs);}
const results=[],startTime=Date.now();
async function test(name,fn){const t=Date.now();await fn();results.push({name,status:'passed',ms:Date.now()-t});}
try{
 start();await ready();browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let id;
 await test('Persona C: fresh dashboard and clear empty-state actions',async()=>{
  await page.goto(url);await page.getByRole('heading',{name:'把研究资料，变成可核对的交付。'}).waitFor();
  assert.equal(await page.locator('[data-action=demo]').count(),1);
  await page.screenshot({path:path.join(out,'dashboard-desktop.png'),fullPage:true});
 });
 await test('Persona A: create task and upload CSV through real file picker',async()=>{
  await page.locator('[data-action=new]').click();await page.locator('#new-form').waitFor();
  await page.locator('#new-form [name=title]').fill('自动化研究流程｜模拟数据');
  await page.locator('#new-form button').click();await page.locator('#data-file').waitFor();
  id=page.url().split('/').at(-1);
  await page.locator('#data-file').setInputFiles(path.join(root,'examples','demo.csv'));
  await page.locator('[data-action=import]').click();await page.getByText(/6 行可计算/).waitFor();
  assert.match(await page.locator('#app').innerText(),/80.00%/);
 });
 await test('Persona A: source attribution, generation, revision and refresh persistence',async()=>{
  await page.getByText('添加一份资料',{exact:true}).click();
  const f=page.locator('#source-form');await f.locator('[name=title]').fill('Synthetic source / 模拟正文');
  await f.locator('[name=url]').fill('https://example.invalid/synthetic-task');
  await f.locator('[name=data_kind]').selectOption('模拟数据');
  await f.locator('[name=content]').fill('这是一份模拟资料。模拟公司本年度收入增长，但这些内容不能作为真实公司事实。');
  await f.locator('button').click();await page.getByText('已登记 1 份资料；已保存 0 次比较。',{exact:true}).waitFor();
  await page.locator('[data-action=generate]').click();await page.locator('.result').first().waitFor();
  await page.locator('.result').first().locator('summary').click();
  const review=page.locator('.review-form').first();await review.locator('[name=text]').fill('仅为模拟资料核对练习，未验证公司事实。');
  await review.locator('[name=status]').selectOption('人工已确认');await review.locator('[name=confirmed]').check();await review.locator('button').click();
  await page.getByText('修订与核对状态已保存。',{exact:true}).waitFor();await page.reload();await page.getByText('仅为模拟资料核对练习，未验证公司事实。',{exact:true}).first().waitFor();
  await page.screenshot({path:path.join(out,'analysis-desktop.png'),fullPage:true});
 });
 await test('Persona A: actual Excel and Markdown downloads',async()=>{
  const promise=page.waitForEvent('download');await page.getByRole('link',{name:'导出 Excel',exact:true}).click();const d=await promise;
  await d.saveAs(path.join(out,'download.xlsx'));assert.ok((await fs.stat(path.join(out,'download.xlsx'))).size>5000);
  const pm=page.waitForEvent('download');await page.getByRole('link',{name:'导出研究报告',exact:true}).click();const md=await pm;await md.saveAs(path.join(out,'download.md'));
  const text=await fs.readFile(path.join(out,'download.md'),'utf8');assert.match(text,/https:\/\/example.invalid\/synthetic-task/);assert.match(text,/模拟数据/);
 });
 await test('Persona A: upload XLSX and reject broken file without losing history',async()=>{
  await page.locator('#data-file').setInputFiles(path.join(root,'examples','demo.xlsx'));
  await page.locator('[data-action=import]').click();await page.getByText(/6 行可计算/).waitFor();
  await page.getByText('demo.xlsx / 6 行 / 6 行可计算',{exact:false}).waitFor();
  const data=await (await fetch(url+'/api/tasks/'+id)).json();assert.equal(data.datasets.length,2);assert.equal(data.datasets.at(-1).rows[0].gross_margin,.8);
  await page.locator('#data-file').setInputFiles({name:'broken.csv',mimeType:'text/csv',buffer:Buffer.from('company,year\nA,2024')});await page.locator('[data-action=import]').click();await page.locator('#notice.error').waitFor();assert.match(await page.locator('#notice').innerText(),/缺少列/);
  const retained=await (await fetch(url+'/api/tasks/'+id)).json();assert.equal(retained.datasets.length,2);
 });
 await test('Persona B: detect problems, update status and retain note after refresh',async()=>{
  await page.locator('[data-action=dirty]').click();await page.getByRole('heading',{name:'数据核验与异常',exact:true}).waitFor();await page.locator('.issue-form').first().waitFor();
  const forms=await page.locator('.issue-form').count();assert.equal(forms,2);
  for(let j=0;j<forms;j++){
   const f=page.locator('.issue-form').nth(j);await f.locator('[name=status]').selectOption('已忽略');await f.locator('[name=note]').fill('模拟测试异常，保留无效行且不纳入指标；真实任务应回查并更正后重新导入。');await f.locator('button').click();await page.getByText('处理意见与状态已保存。',{exact:true}).waitFor();
  }
  await page.reload();await page.locator('.issue-form').first().waitFor();assert.equal(await page.locator('.issue-form').first().locator('[name=status]').inputValue(),'已忽略');
  await page.locator('[data-action=complete]').click();await page.getByText('本次核验已结束；处理记录和导出仍保留。',{exact:true}).waitFor();
  await page.screenshot({path:path.join(out,'issues-desktop.png'),fullPage:true});
 });
 await test('Persona B: completed task reopens when issue is reopened',async()=>{
  const f=page.locator('.issue-form').first();await f.locator('[name=status]').selectOption('处理中');await f.locator('button').click();await page.getByText('处理意见与状态已保存。',{exact:true}).waitFor();
  const data=await (await fetch(url+'/api/tasks/'+id)).json();assert.equal(data.status,'待核验');
 });
 await test('Persona C: feedback create, edit, synthetic label and feature association',async()=>{
  await page.getByRole('link',{name:'需求与产品规划',exact:true}).click();await page.getByText('新增需求、反馈或改进任务',{exact:true}).click();
  const f=page.locator('.op-form').first();await f.locator('[name=kind]').selectOption('反馈');await f.locator('[name=title]').fill('Synthetic: 验证导出入口与说明');await f.locator('[name=pain]').fill('模拟场景：首次使用者需要理解导出范围');await f.locator('[name=story]').fill('希望报告保留财务数据及来源');await f.locator('[name=acceptance]').fill('实际下载 Excel 并检查工作表、公式和来源');await f.locator('[name=feature]').selectOption('export');await f.locator('[name=synthetic]').check();await f.locator('button').click();await page.getByText('需求或反馈记录已保存。',{exact:true}).waitFor();
  const panel=page.locator('section.panel').filter({has:page.getByRole('heading',{name:/Synthetic: 验证导出入口与说明/})});await panel.locator('summary').click();await panel.locator('[name=status]').selectOption('已完成');await panel.locator('button').click();await page.reload();await page.getByText('Synthetic User Feedback / 模拟用户反馈',{exact:true}).first().waitFor();
  await page.screenshot({path:path.join(out,'planning-desktop.png'),fullPage:true});
 });
 await test('Persistence: full server restart retains imported data and issue history',async()=>{
  server.kill();await new Promise(r=>server.once('exit',r));start();await ready();await page.goto(url+'/#issues/'+id);await page.locator('.issue-form').first().waitFor();assert.equal(await page.locator('.issue-form').first().locator('[name=status]').inputValue(),'处理中');
 });
 await test('Persona C: mobile layout, keyboard focus and no viewport overflow',async()=>{
  await page.setViewportSize({width:390,height:844});await page.goto(url+'/#research/'+id);await page.locator('#data-file').waitFor();
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));await page.keyboard.press('Tab');assert.notEqual(await page.evaluate(()=>document.activeElement.tagName),'BODY');
  await page.screenshot({path:path.join(out,'analysis-mobile.png'),fullPage:true});
 });
 await test('Security: cross-origin writes and invalid host rejected',async()=>{
  assert.equal((await fetch(url+'/api/demo',{method:'POST',headers:{Origin:'https://foreign.example','Content-Type':'application/json'},body:'{}'})).status,403);
  const code=await new Promise((resolve,reject)=>{const req=http.request(url+'/api/state',{headers:{Host:'attacker.example'}},res=>{res.resume();resolve(res.statusCode);});req.on('error',reject);req.end();});
  assert.equal(code,403);
 });
 assert.deepEqual(errors,[]);
}catch(e){results.push({name:'failure',status:'failed',error:e.stack});process.exitCode=1;}
finally{
 if(browser)await browser.close();if(server)server.kill();
 const report={label:'Automated synthetic persona tasks; not real-user research',tests:results.length,passed:results.filter(r=>r.status==='passed').length,seconds:(Date.now()-startTime)/1000,results};
 await fs.writeFile(path.join(out,'e2e.json'),JSON.stringify(report,null,2));await fs.writeFile(path.join(out,'e2e-server.log'),logs);console.log(JSON.stringify(report,null,2));
}

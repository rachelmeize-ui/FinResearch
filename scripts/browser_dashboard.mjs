import fs from 'node:fs/promises';import path from 'node:path';import {createRequire} from 'node:module';import {spawn,spawnSync} from 'node:child_process';import assert from 'node:assert/strict';
const cfg=JSON.parse(await fs.readFile('runtime.local.json','utf8')),require=createRequire(path.join(cfg.modules,'__dashboard_qa__.cjs')),{chromium}=require('playwright');
const out='test-results/dashboard-20261122',images='outputs/dashboard-20261122';await fs.mkdir(out,{recursive:true});await fs.mkdir(images,{recursive:true});
const db=path.resolve(out,'workspace-'+Date.now()+'.sqlite3');assert.equal(spawnSync(cfg.python,['scripts/clone_test_db.py',db],{windowsHide:true}).status,0);
const base='http://127.0.0.1:8539',server=spawn(cfg.python,['server.py','--port','8539'],{windowsHide:true,env:{...process.env,FINRESEARCH_DB:db,FINRESEARCH_TEST_MODE:'0',FINRESEARCH_EXCEL_BACKEND:'portable'}});let logs='',browser,page,selected,task;const results=[],errors=[];server.stderr.on('data',x=>logs+=x);
const get=async p=>(await fetch(base+p)).json();const valid=t=>t.datasets.at(-1).rows.filter(r=>r.valid);const fmt=(n,p=false)=>p?(n*100).toFixed(2)+'%':n.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2});
async function test(name,kind,fn){await fn();results.push({name,kind,status:'passed'});console.log('PASS '+name);}
async function loaded(){await page.locator('#dashboard-revenue svg').waitFor();await page.waitForFunction(()=>document.querySelector('#dashboard-content')?.getAttribute('aria-busy')==='false');}
async function screen(name,fullPage=true){await page.screenshot({path:images+'/'+name+'.png',fullPage});}
async function option(id){return page.locator('#dashboard-'+id).evaluate(el=>echarts.getInstanceByDom(el).getOption());}
try{
 for(let n=0;n<100;n++){try{if((await fetch(base+'/healthz')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});page=await browser.newPage({viewport:{width:1440,height:900},acceptDownloads:true,reducedMotion:'reduce'});page.on('pageerror',e=>errors.push(e.message));
 await test('首页前置真实财务表与四种图表，不创建任务或调用模型','real backend / existing saved financial data',async()=>{
  const before=(await get('/api/state')).tasks.length;await page.goto(base+'/#home');await loaded();selected=await page.locator('#dashboard-task').inputValue();task=await get('/api/tasks/'+selected);
  assert.equal(await page.locator('.dashboard-chart svg').count(),4);assert.equal(await page.locator('#home-create-panel').getAttribute('open'),null);
  const y=Number(await page.locator('#dashboard-year').inputValue()),r=valid(task).find(r=>r.year===y&&r.company===task.company_a);
  assert.equal(await page.locator('.dashboard-table-panel [data-dashboard-field=revenue]').first().innerText(),fmt(r.revenue));assert.equal((await get('/api/state')).tasks.length,before);
  assert.ok((await page.locator('#dashboard-keywords').boundingBox()).y<1100);await screen('after-dashboard-1440');await screen('after-dashboard-1440-viewport',false);
 });
 await test('彩色横条、宽幅柱状、扇形与词云均为真实数据交互','real browser / deterministic data and corpus',async()=>{
  const annual=await option('annual');assert.equal(annual.series[0].type,'bar');assert.equal(annual.yAxis[0].type,'category');assert.ok(new Set(annual.series[0].data.map(d=>d.itemStyle.color)).size>3);
  assert.equal((await option('revenue')).series.length,4);
  assert.ok(await page.locator('[data-dashboard-keyword]').count()>5);
  const word=page.locator('#dashboard-keywords [data-dashboard-keyword]').first(),text=await word.innerText();await word.click();assert.ok((await page.locator('#drawer-body').innerText()).includes(text));assert.match(await page.locator('#drawer-body').innerText(),/不是年报全文/);await page.keyboard.press('Escape');
  await page.locator('#dashboard-balance-shape').selectOption('donut');assert.equal((await option('balance')).series[0].radius[0],'56%');await page.locator('#dashboard-balance-shape').selectOption('pie');assert.equal((await option('balance')).series[0].radius[0],'0%');
 });
 await test('表格年度与资产结构联动，保持研究期间图表','real browser / deterministic values',async()=>{
  const y=Math.min(...valid(task).filter(r=>r.company===task.company_a&&valid(task).some(b=>b.company===task.company_b&&b.year===r.year)).map(r=>r.year));await page.locator('#dashboard-year').selectOption(String(y));const r=valid(task).find(r=>r.year===y&&r.company===task.company_a);
  assert.equal(await page.locator('.dashboard-table-panel [data-dashboard-field=revenue]').first().innerText(),fmt(r.revenue));
  const pie=(await option('balance')).series[0];assert.ok(Math.abs(pie.data.reduce((n,d)=>n+d.value,0)-r.assets)<1e-7);
  await page.locator('#dashboard-balance-company').selectOption(task.company_b);const rb=valid(task).find(r=>r.year===y&&r.company===task.company_b);assert.equal((await option('balance')).series[0].data[0].value,rb.liabilities);
 });
 await test('利润指标切换使用保存的比率，颜色固定对应公司','real browser / deterministic values',async()=>{
  await page.locator('#dashboard-profit-metric').selectOption('gross_margin');const chart=await option('profit');const point=chart.series[0].data.find(d=>d.value!==null),r=valid(task).find(r=>r.company===point.company&&r.year===point.year);
  assert.ok(Math.abs(point.value-r.gross_margin*100)<1e-9);assert.equal(chart.series[0].itemStyle.color,'#3080ED');assert.equal(chart.series[1].itemStyle.color,'#9955DC');
 });
 await test('表格数字键盘打开正确研究的原文，Escape恢复焦点','real browser / saved disclosure evidence',async()=>{
  const button=page.locator('.dashboard-table-panel [data-dashboard-field=revenue]').first();await button.focus();await page.keyboard.press('Enter');await page.locator('dialog[open]').waitFor();
  assert.match(await page.locator('#drawer-body').innerText(),new RegExp(task.company_a));assert.match(await page.locator('#drawer-body').innerText(),/原始金额/);await screen('dashboard-field-evidence');await page.keyboard.press('Escape');assert.ok(await button.evaluate(el=>document.activeElement===el));
 });
 await test('实际点击柱形打开字段来源，不靠程序触发假点击','real browser / pointer on SVG bar',async()=>{
  await page.locator('#dashboard-revenue').scrollIntoViewIfNeeded();
  const shapes=await page.locator('#dashboard-revenue svg path').evaluateAll(nodes=>nodes.map(n=>{const b=n.getBoundingClientRect();return {fill:n.getAttribute('fill'),x:b.x,y:b.y,w:b.width,h:b.height};}).filter(b=>b.fill?.toLowerCase()==='#3080ed'&&b.h>15&&b.w>10));assert.ok(shapes.length);
  const bar=shapes[0];await page.mouse.click(bar.x+bar.w/2,bar.y+bar.h/2);await page.locator('dialog[open]').waitFor();assert.match(await page.locator('#drawer-body').innerText(),/营业收入/);await page.keyboard.press('Escape');
 });
 await test('图表数据表可逐项查看来源，关闭后返回最初入口','real browser / keyboard alternative',async()=>{
  const opener=page.locator('[data-dashboard-data=balance]');await opener.click();await page.locator('#drawer-body [data-dashboard-field=net_assets]').click();assert.match(await page.locator('#drawer-body').innerText(),/总资产－总负债/);await page.keyboard.press('Escape');assert.ok(await opener.evaluate(el=>document.activeElement===el));
 });
 await test('切换网易同步报表、币种字段、XBRL来源及导出对象','real backend / existing SEC data',async()=>{
  const state=await get('/api/state'),netease=state.tasks.find(t=>t.company_a==='网易'&&!t.company_b&&t.data_rows===3);assert.ok(netease);await page.locator('#dashboard-task').selectOption(netease.id);await loaded();selected=netease.id;task=await get('/api/tasks/'+selected);
  assert.equal(await page.locator('.dashboard-compare-table thead th').count(),2);assert.ok(valid(task).every(r=>r.currency==='CNY'));
  await page.locator('.dashboard-table-panel [data-dashboard-field=revenue]').first().click();assert.match(await page.locator('#drawer-body').innerText(),/us-gaap:/);await page.keyboard.press('Escape');
  assert.equal(await page.locator('#dashboard-controls a[download]').getAttribute('href'),'/api/tasks/'+selected+'/report.xlsx');await screen('dashboard-netease');
 });
 await test('刷新保留选择，实际下载当前对象Excel','real browser / actual download',async()=>{
  await page.reload();await loaded();assert.equal(await page.locator('#dashboard-task').inputValue(),selected);
  const wait=page.waitForEvent('download');await page.locator('#dashboard-controls a[download]').click();const d=await wait;assert.equal(await d.failure(),null);await d.saveAs(out+'/dashboard-export.xlsx');assert.equal((await fs.readFile(out+'/dashboard-export.xlsx')).subarray(0,2).toString(),'PK');
 });
 await test('前置看板保留创建入口与草稿，切换数据不清空表单','real browser / form continuity',async()=>{
  await page.locator('[data-home-action=create]').click();await page.locator('[name=question]').fill('核对这个问题的公开依据');assert.ok(await page.locator('#home-create-panel').evaluate(el=>el.open));
  await page.locator('#dashboard-task').selectOption(task.id);await loaded();assert.equal(await page.locator('[name=question]').inputValue(),'核对这个问题的公开依据');
  await page.reload();await loaded();assert.equal(await page.locator('[name=question]').inputValue(),'核对这个问题的公开依据');
 });
 await test('360/390/768px不产生页面横向溢出，新建研究始终可达','real browser / responsive',async()=>{
  for(const width of [390,360,768]){await page.setViewportSize({width,height:844});await page.evaluate(()=>scrollTo(0,0));await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.ok(await page.locator('[data-home-action=create]').isVisible());if(width===390){await screen('after-dashboard-390');await screen('after-dashboard-390-viewport',false);}if(width===768)await screen('after-dashboard-768');}
  await page.setViewportSize({width:1440,height:900});
 });
 await test('十年窄屏刻度无重叠、词云前18词完整可见','real browser / ten-year layout geometry',async()=>{
  const state=await get('/api/state'),decade=state.tasks.find(t=>t.meta.requested_years?.length===10&&t.data_rows===20);assert.ok(decade);await page.locator('#dashboard-task').selectOption(decade.id);await loaded();
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:width===390?844:900});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);await page.waitForTimeout(200);
   for(const chart of ['profit','revenue']){const overlaps=await page.locator('#dashboard-'+chart+' svg text').evaluateAll(nodes=>{const boxes=nodes.filter(n=>/^20(?:1[6-9]|2[0-5])$/.test(n.textContent)).map(n=>n.getBoundingClientRect());return boxes.some((a,i)=>boxes.some((b,j)=>i<j&&Math.min(a.right,b.right)>Math.max(a.left,b.left)+1&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top)+1));});assert.equal(overlaps,false,chart+' labels overlap at '+width);}
   assert.ok(await page.locator('#dashboard-keywords button').count()<=18);
   assert.equal(await page.locator('#dashboard-keywords').evaluate(el=>{const b=el.getBoundingClientRect();return [...el.querySelectorAll('button')].every(n=>{const r=n.getBoundingClientRect();return r.top>=b.top-1&&r.bottom<=b.bottom+1;});}),true);
   if(width===390){await screen('after-dashboard-390');await screen('after-dashboard-390-viewport',false);}else{await screen('after-dashboard-1440');await screen('after-dashboard-1440-viewport',false);}
  }
  await page.setViewportSize({width:1440,height:900});await page.locator('#dashboard-task').selectOption(selected);await loaded();
 });
 await test('加载失败可重试，并保持创建入口可用','simulated API503 / real browser recovery',async()=>{
  await page.route('**/api/tasks/'+selected,route=>route.fulfill({status:503,json:{error:'测试：研究数据暂时不可读。'}}));await page.reload();await page.locator('.dashboard-error').waitFor();assert.ok(await page.locator('[data-home-action=create]').isVisible());await screen('dashboard-load-error');await page.unroute('**/api/tasks/'+selected);await page.locator('[data-dashboard-action=retry]').click();await loaded();
 });
 await test('缺失年度保留null，折线不跨缺失项补值','simulated omission of actual rows / no fabricated finance',async()=>{
  const original=await get('/api/tasks/'+selected),mock=structuredClone(original),missing=valid(mock)[1];mock.datasets.at(-1).rows=mock.datasets.at(-1).rows.filter(r=>r.year!==missing.year);mock.coverage.complete=false;mock.coverage.actual_period='测试：移除了一个年度';
  await page.route('**/api/tasks/'+selected,route=>route.fulfill({json:mock}));await page.reload();await loaded();const chart=await option('profit');assert.equal(chart.series[0].data.find(d=>d.year===missing.year).value,null);assert.equal(chart.series[0].connectNulls,false);await screen('dashboard-missing-year');await page.unroute('**/api/tasks/'+selected);
 });
 await test('无财务数据时不生成假图表，表单自动打开','simulated empty state / real browser',async()=>{
  await page.route('**/api/state',async route=>{const response=await route.fetch(),state=await response.json();state.tasks=[];await route.fulfill({json:state});});await page.reload();await page.locator('.dashboard-welcome').waitFor();assert.equal(await page.locator('.dashboard-chart svg').count(),0);assert.ok(await page.locator('#home-create-panel').evaluate(el=>el.open));await screen('dashboard-empty');await page.unroute('**/api/state');
 });
 assert.deepEqual(errors,[]);assert.equal((await get('/api/engine')).authorized_calls_remaining,0);
 await fs.writeFile(out+'/results.json',JSON.stringify({status:'passed',tests:results.length,results,pageErrors:errors,newModelCalls:0,database:db},null,2));console.log(JSON.stringify({status:'passed',tests:results.length}));
}catch(error){if(page)await page.screenshot({path:images+'/failure.png',fullPage:true}).catch(()=>{});await fs.writeFile(out+'/results.json',JSON.stringify({status:'failed',results,error:String(error),pageErrors:errors},null,2));throw error;}finally{if(browser)await browser.close();server.kill();await fs.writeFile(out+'/server.log',logs);}

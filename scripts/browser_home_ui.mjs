import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {spawn,spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';

const cfg=JSON.parse(await fs.readFile('runtime.local.json','utf8'));
const require=createRequire(path.join(cfg.modules,'__home_ui__.cjs'));
const {chromium}=require('playwright');
const out='test-results/home-ui-20261122',images='outputs/home-design-20261122';
await fs.mkdir(out,{recursive:true});await fs.mkdir(images,{recursive:true});
const database=path.resolve(out,'workspace-'+Date.now()+'.sqlite3');
assert.equal(spawnSync(cfg.python,['scripts/clone_test_db.py',database],{windowsHide:true}).status,0);
const base='http://127.0.0.1:8536';
const server=spawn(cfg.python,['server.py','--port','8536'],{windowsHide:true,env:{...process.env,FINRESEARCH_DB:database,FINRESEARCH_TEST_MODE:'0',FINRESEARCH_EXCEL_BACKEND:'portable'}});
let logs='',browser,page;const results=[],errors=[];
server.stderr.on('data',buffer=>logs+=buffer);server.stdout.on('data',buffer=>logs+=buffer);
const api=async url=>(await fetch(base+url)).json();
async function test(name,kind,fn){await fn();results.push({name,kind,status:'passed'});console.log('PASS '+name);}
async function home(){await page.goto(base+'/#home');await page.locator('#new-form').waitFor({state:'attached'});if(!await page.locator('#new-form').isVisible())await page.locator('[data-home-action=create]').click();await page.locator('#new-form').waitFor();}
const submit=()=>page.locator('#new-form button[type=submit]');
async function screenshot(name,fullPage=true){await page.screenshot({path:images+'/'+name+'.png',fullPage});}

try {
  for(let n=0;n<100;n++){try{if((await fetch(base+'/healthz')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  page=await browser.newPage({viewport:{width:1440,height:900},acceptDownloads:true,reducedMotion:'reduce'});page.on('pageerror',e=>errors.push(e.message));
  await test('首页以空白问题开始，最近研究读取真实保存任务','real browser / existing data',async()=>{
    await home();assert.equal(await page.locator('[name=question]').inputValue(),'');assert.equal(await page.locator('[name=company_a]').inputValue(),'');
    assert.ok(await page.locator('[name=company_b]').isDisabled());
    const state=await api('/api/state');assert.equal(await page.locator('.home-study-row .study-title').first().getAttribute('href'),'#research/'+state.tasks[0].id);
    assert.equal(await page.locator('input[name=research_type]').count(),3);
    await screenshot('after-home-1440');await screenshot('after-home-1440-viewport',false);
  });
  await test('比较公司按需展开，移除不提交旧值，再展开保留填写','real browser',async()=>{
    await page.locator('[data-home-action=compare]').click();await page.locator('[name=company_b]').fill('网易');
    await page.locator('[data-home-action=compare]').click();assert.ok(await page.locator('[name=company_b]').isDisabled());
    assert.equal(await page.locator('#new-form').evaluate(f=>new FormData(f).has('company_b')),false);
    await page.locator('[data-home-action=compare]').click();assert.equal(await page.locator('[name=company_b]').inputValue(),'网易');
  });
  await test('键盘切换研究类型，行业主题标签正确，保留自拟问题','real browser / keyboard',async()=>{
    await page.locator('[name=question]').fill('研究2022—2025年产品结构差异，说明证据限制。');
    await page.locator('[name=research_type][value=financial]').focus();await page.keyboard.press('ArrowRight');assert.ok(await page.locator('[value=business]').isChecked());
    assert.match(await page.locator('#mode-description').innerText(),/商业模式/);
    await page.locator('[value=industry]').check();assert.equal(await page.locator('#company-label').innerText(),'行业或市场主题');
    assert.ok(await page.locator('[name=company_b]').isDisabled());assert.match(await page.locator('[name=question]').inputValue(),/产品结构差异/);
    assert.equal(await page.locator('[name=start_year]').inputValue(),'2022');
  });
  await test('刷新与导航后恢复当前会话草稿，字符数同步','real browser / session storage',async()=>{
    await page.locator('[name=company_a]').fill('中国游戏行业');await page.reload();await page.locator('#new-form').waitFor();
    assert.equal(await page.locator('[name=company_a]').inputValue(),'中国游戏行业');assert.ok(await page.locator('[value=industry]').isChecked());
    const value=await page.locator('[name=question]').inputValue();assert.equal(await page.locator('#question-count').innerText(),value.length+' / 1000');
    await page.locator('.sidebar a[data-page=studies]').click();await page.locator('#study-search').waitFor();await page.locator('.sidebar a[data-page=home]').click();
    await page.locator('#new-form').waitFor();assert.equal(await page.locator('[name=question]').inputValue(),value);
  });
  await test('必填与年度错误阻止提交，并就近提示','real browser / validation',async()=>{
    await page.locator('[name=question]').fill('');const count=(await api('/api/state')).tasks.length;await submit().click();
    assert.match(await page.locator('#home-form-feedback').innerText(),/请填写/);assert.equal((await api('/api/state')).tasks.length,count);
    await page.locator('[name=question]').fill('核对研究年度');await page.locator('[name=start_year]').fill('2026');await page.locator('[name=end_year]').fill('2023');await submit().click();
    assert.match(await page.locator('#home-form-feedback').innerText(),/结束年度不能早于/);
    await screenshot('after-home-validation');
  });
  await test('示例只填写条件、不启动研究；切换类型有匹配示例','real browser',async()=>{
    const count=(await api('/api/state')).tasks.length;await page.locator('[value=business]').check();await page.locator('[data-home-action=example]').click();
    assert.equal(await page.locator('[name=company_a]').inputValue(),'米哈游');assert.equal(await page.locator('[name=company_b]').inputValue(),'网易');
    assert.equal((await api('/api/state')).tasks.length,count);assert.match(await page.locator('[name=question]').inputValue(),/商业模式/);
  });
  await test('识别服务失败时保留输入、恢复按钮并允许重试','simulated API failure / real browser',async()=>{
    await page.locator('[value=financial]').check();await page.locator('[name=start_year]').fill('2023');await page.locator('[name=end_year]').fill('2025');await page.locator('[data-home-action=example]').click();
    await page.route('**/api/identify',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'测试：识别服务暂时不可用，请重试。'})}));
    await submit().click();await page.locator('#home-form-feedback').getByText(/识别服务暂时不可用/).waitFor();
    assert.ok(await submit().isEnabled());assert.equal(await page.locator('[name=company_a]').inputValue(),'贵州茅台');assert.equal(await submit().locator('svg').count(),1);
    await screenshot('after-home-api-error');await page.unroute('**/api/identify');
  });
  let createdId;
  await test('创建已保存但启动取数失败：进入原任务，重试不重复创建','simulated collect503 / real creation and public-filings retry',async()=>{
    await page.locator('[name=company_a]').fill('网易');if(await page.locator('[name=company_b]').isEnabled())await page.locator('[data-home-action=compare]').click();
    const before=(await api('/api/state')).tasks.length;let calls=0;
    await page.route('**/api/tasks/*/collect',route=>++calls===1?route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'测试：资料获取启动失败。'})}):route.continue());
    await submit().click();await page.waitForURL(/#research\//);await page.locator('.context-meta').waitFor();
    const id=page.url().split('/').at(-1);await page.locator('#notice').getByText(/研究已保存/).waitFor();
    assert.equal((await api('/api/state')).tasks.length,before+1);await screenshot('saved-study-collect-error');
    await page.locator('[data-action=collect]').click();let task;
    for(let n=0;n<600;n++){task=await api('/api/tasks/'+id);if(task.jobs.length&&!task.jobs.some(j=>j.status==='running'))break;await new Promise(r=>setTimeout(r,200));}
    assert.equal(task.jobs.at(-1).status,'succeeded');assert.equal(task.datasets.at(-1).rows.length,3);assert.equal((await api('/api/state')).tasks.length,before+1);
    assert.equal(page.url().split('/').at(-1),id);await page.unroute('**/api/tasks/*/collect');await home();
  });
  await test('主体歧义后切换行业会清除过期必填选项，仍可保存','simulated ambiguity and collect503 / real industry task creation',async()=>{
    await page.locator('[name=company_a]').fill('测试主体歧义');await page.locator('[name=question]').fill('研究公开业务与行业信息缺口');
    await page.route('**/api/identify',route=>route.fulfill({json:{exact:false,candidates:[{id:'test-a',name:'测试主体A',code:'000001',market:'A股'},{id:'test-b',name:'测试主体B',code:'000002',market:'A股'}]}}));
    await submit().click();await page.locator('.entity-picks select').waitFor();assert.equal(await page.locator('.entity-picks select').inputValue(),'');
    await page.locator('[name=research_type][value=industry]').check();assert.equal(await page.locator('.entity-picks').count(),0);
    await page.route('**/api/tasks/*/collect',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'测试：未启动外部行业检索。'})}));
    await submit().click();await page.waitForURL(/#research\//);const task=await api('/api/tasks/'+page.url().split('/').at(-1));
    assert.equal(task.meta.research_type,'industry');assert.equal(task.company_a,'测试主体歧义');
    await page.unroute('**/api/identify');await page.unroute('**/api/tasks/*/collect');await home();
  });
  await test('真实创建→逐年财报处理→同一研究工作区；刷新保留结果','real backend / actual public-document cache / no model call',async()=>{
    await page.locator('[data-home-action=example]').click();await submit().click();await page.waitForURL(/#research\//,{timeout:60000});createdId=page.url().split('/').at(-1);
    let task;for(let n=0;n<600;n++){task=await api('/api/tasks/'+createdId);if(task.jobs.length&&!task.jobs.some(j=>j.status==='running'))break;await new Promise(r=>setTimeout(r,200));}
    assert.equal(task.jobs.at(-1).status,'succeeded');assert.equal(task.datasets.at(-1).rows.length,6);assert.equal(task.documents.filter(d=>d.kind==='annual_pdf').length,6);assert.deepEqual(task.meta.requested_years,[2023,2024,2025]);
    await page.reload();await page.locator('.research-tabs').waitFor();await page.locator('button[data-field=revenue]').first().waitFor();
    assert.match(await page.locator('.context-meta').innerText(),/2023—2025/);await screenshot('created-study');
    await page.locator('button[data-field=revenue]').first().click();await page.locator('dialog[open]').waitFor();await page.keyboard.press('Escape');
    await page.locator('.research-tabs').getByRole('link',{name:'研究报告',exact:true}).click();await page.locator('.report-paper').waitFor();
    for(const [label,file] of [['下载研究报告','created-study.md'],['下载 Excel','created-study.xlsx']]){const wait=page.waitForEvent('download');await page.getByRole('link',{name:label,exact:true}).click();const download=await wait;assert.equal(await download.failure(),null);await download.saveAs(out+'/'+file);}
    assert.match(await fs.readFile(out+'/created-study.md','utf8'),/2023—2025/);assert.equal((await fs.readFile(out+'/created-study.xlsx')).subarray(0,2).toString(),'PK');
    await home();assert.equal(await page.locator('[name=question]').inputValue(),'');assert.equal(await page.locator('.home-study-row .study-title').first().getAttribute('href'),'#research/'+createdId);
  });
  await test('390px首屏有新建研究入口，表单可打开，360/390/768无横向溢出','real browser / responsive',async()=>{
    for(const [width,height] of [[390,844],[360,800],[768,1024]]){
      await page.setViewportSize({width,height});await page.evaluate(()=>scrollTo(0,0));
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'page overflow at '+width);
      if(width===390){const box=await page.locator('[data-home-action=create]').boundingBox();assert.ok(box.y+box.height<=height,JSON.stringify(box));await page.locator('[data-home-action=create]').click();await submit().scrollIntoViewIfNeeded();assert.ok(await submit().isVisible());await screenshot('after-home-390');await screenshot('after-home-390-viewport',false);}
      if(width===768)await screenshot('after-home-768');
    }
  });
  await test('空研究列表提供明确指引，不重复创建主按钮','simulated empty API state / real browser',async()=>{
    await page.route('**/api/state',async route=>{const response=await route.fetch();const state=await response.json();state.tasks=[];await route.fulfill({json:state});});
    await home();await page.reload();await page.locator('#new-form').waitFor();await page.getByRole('heading',{name:'还没有研究记录',exact:true}).waitFor();assert.equal(await page.locator('button[type=submit]').count(),1);await screenshot('after-home-empty');await page.unroute('**/api/state');
  });
  assert.equal((await api('/api/engine')).authorized_calls_remaining,0);assert.deepEqual(errors,[]);
  const result={status:'passed',tests:results.length,results,pageErrors:errors,newPaidModelCalls:0,isolatedDatabase:database,createdStudy:createdId};
  await fs.writeFile(out+'/results.json',JSON.stringify(result,null,2));console.log(JSON.stringify({status:'passed',tests:results.length,newPaidModelCalls:0}));
} catch(error) {
  if(page)await page.screenshot({path:images+'/failure.png',fullPage:true}).catch(()=>{});
  await fs.writeFile(out+'/results.json',JSON.stringify({status:'failed',results,error:String(error),pageErrors:errors},null,2));throw error;
} finally {if(browser)await browser.close();server.kill();await fs.writeFile(out+'/server.log',logs);}

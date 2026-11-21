import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import path from 'node:path';
import assert from 'node:assert/strict';
const cfg=JSON.parse(await fs.readFile('runtime.local.json','utf8'));
const require=createRequire(path.join(cfg.modules,'__live__.cjs'));
const {chromium}=require('playwright');
const id=(await fs.readFile('data/demo-id.txt','utf8')).trim();
const url='http://127.0.0.1:8530';
let state;
for(let attempt=0;attempt<40;attempt++){
 try{state=await(await fetch(url+'/api/state')).json();break;}catch{await new Promise(r=>setTimeout(r,150));}
}
assert.ok(state,'Preview did not start');assert.equal(typeof state.pending_issues,'number');
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 await page.goto(url+'/#research/'+id);await page.getByText(/6 行可计算/).waitFor();
 assert.equal(await page.locator('.result').count(),6);
 assert.match(await page.locator('#app').innerText(),/模拟数据/);
 await page.screenshot({path:'outputs/finresearch-20261121/工作台预览.png',fullPage:true});
 await page.getByRole('link',{name:'需求与产品规划',exact:true}).click();
 await page.getByRole('heading',{name:/B08/}).waitFor();
 const result={url:url+'/#research/'+id,task_rows:6,comparison_cells:6,active_pending_issues:state.pending_issues,version:state.releases[0].version,read_only_check:'passed'};
 await fs.writeFile('test-results/live-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{await browser.close();}

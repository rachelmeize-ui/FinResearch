import fs from 'node:fs/promises';import path from 'node:path';import {createRequire} from 'node:module';
const cfg=JSON.parse(await fs.readFile('runtime.local.json','utf8')),require=createRequire(path.join(cfg.modules,'__ui__.cjs')),{chromium}=require('playwright');
const out='test-results/ui-redesign/before';await fs.mkdir(out,{recursive:true});
const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
try{const p=await b.newPage();const id=(await fs.readFile('data/real-case-id.txt','utf8')).trim(),checks=[];
for(const width of [1440,390]){await p.setViewportSize({width,height:900});for(const route of ['home','research/'+id,'finance/'+id,'reports/'+id]){
await p.goto('http://127.0.0.1:8530/#'+route);await p.locator('h1').waitFor();await p.screenshot({path:`${out}/${width}-${route.split('/')[0]}.png`,fullPage:true});checks.push({width,route,title:await p.locator('h1').innerText(),height:await p.evaluate(()=>document.documentElement.scrollHeight),overflow:await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth)});
} }await fs.writeFile(out+'/audit.json',JSON.stringify(checks,null,2));console.log(JSON.stringify(checks));}finally{await b.close();}

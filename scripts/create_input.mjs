import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {pathToFileURL,fileURLToPath} from 'node:url';
import path from 'node:path';
const cfg=JSON.parse(await fs.readFile(new URL('../runtime.local.json',import.meta.url),'utf8'));
const req=createRequire(path.join(cfg.modules,'__input__.cjs'));
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(req.resolve('@oai/artifact-tool')).href);
const csv=await fs.readFile(new URL('../examples/demo.csv',import.meta.url),'utf8');
const w=await Workbook.fromCSV(csv,{sheetName:'模拟输入'}),s=w.worksheets.getItemAt(0);
for(const col of ['B','G','H','I','J','K']){
 const r=s.getRange(`${col}2:${col}7`);r.values=r.values.map(row=>[Number(row[0])]);
}
s.getRange('A1:M7').format.columnWidth=20;
s.getRange('A1:M1').format={fill:'#173C35',font:{bold:true,color:'#FFFFFF'},rowHeight:28};
s.getRange('L1:L7').format.columnWidth=50;
s.freezePanes.freezeRows(1);w.recalculate();
await (await SpreadsheetFile.exportXlsx(w)).save(fileURLToPath(new URL('../examples/demo.xlsx',import.meta.url)));
